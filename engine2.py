import json
import os
import re

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI  # Add this import
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class SHLRecommendationEngine:
    def __init__(self, index_path="faiss_index", use_local_embeddings=True):
        # Embeddings setup (keep local for now)
        if use_local_embeddings:
            print("Loading local embeddings model...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},  # Use CPU for Cloud Run
            )
        else:
            from langchain_openai import OpenAIEmbeddings

            self.embeddings = OpenAIEmbeddings()

        # Load vector store
        print(f"Loading vector store from {index_path}...")
        try:
            self.vectorstore = FAISS.load_local(
                index_path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            raise

        # Use Gemini API for LLM
        print("Using Google Gemini LLM...")
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.1,
            )
            self.llm.invoke("Test")  # Test API key
        except Exception as e:
            print(f"Gemini LLM failed: {e}")
            raise

        # Retriever setup
        print("Setting up retriever...")
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10},
        )
        self._setup_rag_chain()

    def _setup_rag_chain(self):
        """Set up the RAG chain for processing queries"""
        template = """
        You are an expert SHL assessment recommendation system. You help HR professionals and hiring managers
        find the most suitable assessments for their hiring needs.

        Based on the user's query and the retrieved assessment information, recommend the most relevant
        SHL assessments. Follow these criteria:

        1. Analyze the job requirements, skills, and role level mentioned in the query
        2. Consider assessment duration constraints if mentioned
        3. Match assessments to the technical skills and soft skills required
        4. Prioritize assessments specifically designed for the mentioned job roles
        5. Return at most 10 assessments, prioritizing the most relevant ones

        USER QUERY: {query}

        RETRIEVED ASSESSMENTS:
        {context}

        Provide a JSON object with your recommendations in this format:
        ```json
        {{
          "recommended_assessments": [
            {{
              "url": "URL to the assessment",
              "adaptive_support": "Yes or No",
              "description": "Description of the assessment",
              "duration": 30,
              "remote_support": "Yes or No",
              "test_type": ["Category1", "Category2"]
            }}
          ]
        }}
        ```

        The duration field should be an integer, not a string.
        The test_type field should be an array of strings, even if there's only one type.
        Return only the JSON object, no additional text outside the json markers.
        """
        prompt = ChatPromptTemplate.from_template(template)
        print("Setting up RAG chain...")
        self.rag_chain = (
            {"context": self.retriever, "query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def recommend(self, query, max_results=10):
        """Process a query and return recommended assessments"""
        try:
            print(f"Processing query: {query[:50]}...")
            raw_response = self.rag_chain.invoke(query)
            print(f"Raw LLM Response: {raw_response[:200]}...")

            # Parse JSON from the response
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_response)
            if json_match:
                json_str = json_match.group(1)
                print("Extracted JSON from ```json ... ``` block.")
            else:
                json_str = raw_response
                print("No ```json block found, attempting to parse entire response.")

            try:
                recommendations = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                print(f"Failed to parse JSON: {json_err}")
                print("Attempting fallback regex parsing...")
                json_pattern = r'{\s*"recommended_assessments"\s*:\s*\[(.*?)\]\s*}'
                match = re.search(json_pattern, raw_response, re.DOTALL)
                if match:
                    print("Fallback regex found potential recommendations structure.")
                    recommendations = {"recommended_assessments": []}
                    item_pattern = r"{\s*(.*?)}"
                    items_content = re.findall(item_pattern, match.group(1), re.DOTALL)

                    for item_str in items_content:
                        rec = {}
                        for field in [
                            "url",
                            "adaptive_support",
                            "description",
                            "duration",
                            "remote_support",
                            "test_type",
                        ]:
                            if field == "test_type":
                                # Handle test_type as array
                                field_match = re.search(
                                    rf'"{field}"\s*:\s*\[(.*?)\]', item_str, re.DOTALL
                                )
                                if field_match:
                                    types_str = field_match.group(1).strip()
                                    types_list = re.findall(r'"([^"]+)"', types_str)
                                    rec[field] = types_list
                                else:
                                    rec[field] = []
                            elif field == "duration":
                                # Handle duration as integer
                                field_match = re.search(
                                    rf'"{field}"\s*:\s*(\d+)', item_str
                                )
                                if field_match:
                                    rec[field] = int(field_match.group(1).strip())
                                else:
                                    rec[field] = 0
                            else:
                                # Handle string fields
                                field_match = re.search(
                                    rf'"{field}"\s*:\s*"(.*?)"', item_str
                                )
                                if field_match:
                                    rec[field] = field_match.group(1).strip()
                                else:
                                    rec[field] = ""
                        if rec.get("url") != "":
                            recommendations["recommended_assessments"].append(rec)
                else:
                    print("Fallback regex parsing failed to find structure.")
                    recommendations = {"recommended_assessments": []}

            # Ensure output has correct key
            if (
                "recommendations" in recommendations
                and "recommended_assessments" not in recommendations
            ):
                recommendations["recommended_assessments"] = recommendations.pop(
                    "recommendations"
                )

            # Limit to max_results
            if "recommended_assessments" in recommendations:
                recommendations["recommended_assessments"] = recommendations[
                    "recommended_assessments"
                ][:max_results]
                print(
                    f"Found {len(recommendations['recommended_assessments'])} recommendations after parsing and filtering."
                )
            else:
                print("No 'recommended_assessments' key found in parsed output.")
                recommendations = {"recommended_assessments": []}

            # Ensure correct data types
            for rec in recommendations.get("recommended_assessments", []):
                if "duration" in rec and not isinstance(rec["duration"], int):
                    try:
                        rec["duration"] = int(rec["duration"])
                    except (ValueError, TypeError):
                        rec["duration"] = 0

                if "test_type" in rec and not isinstance(rec["test_type"], list):
                    if isinstance(rec["test_type"], str):
                        rec["test_type"] = [rec["test_type"]]
                    else:
                        rec["test_type"] = []

            return recommendations
        except Exception as e:
            print(f"Error processing query in recommend method: {e}")
            return {"error": str(e), "recommended_assessments": []}


if __name__ == "__main__":
    # Test the recommendation engine
    engine = SHLRecommendationEngine(use_local_embeddings=True)
    query = "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes."
    results = engine.recommend(query)
    print("\n--- Final Results ---")
    print(json.dumps(results, indent=2))

    print("\n--- Testing another query ---")
    query_sales = "Need assessment for entry-level sales role focusing on communication and resilience."
    results_sales = engine.recommend(query_sales)
    print("\n--- Final Results (Sales) ---")
    print(json.dumps(results_sales, indent=2))
