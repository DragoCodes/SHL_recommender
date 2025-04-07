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

    # Rest of your code ( `_setup_rag_chain` and `recommend`) remains unchanged
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
          "recommendations": [
            {{
              "assessment_name": "Name of the assessment",
              "url": "URL to the assessment",
              "remote_testing_support": "Yes or No",
              "adaptive_irt_support": "Yes or No",
              "duration": "Duration in minutes",
              "test_type": "Type of test",
            }}
          ]
        }}
        ```

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
                json_pattern = r'{\s*"recommendations"\s*:\s*\[(.*?)\]\s*}'
                match = re.search(json_pattern, raw_response, re.DOTALL)
                if match:
                    print("Fallback regex found potential recommendations structure.")
                    recommendations = {"recommendations": []}
                    item_pattern = r"{\s*(.*?)}"
                    items_content = re.findall(item_pattern, match.group(1), re.DOTALL)

                    for item_str in items_content:
                        rec = {}
                        for field in [
                            "assessment_name",
                            "url",
                            "remote_testing_support",
                            "adaptive_irt_support",
                            "duration",
                            "test_type",
                        ]:
                            field_match = re.search(
                                rf'"{field}"\s*:\s*"(.*?)"', item_str
                            )
                            if field_match:
                                rec[field] = field_match.group(1).strip()
                            else:
                                field_match_no_quotes = re.search(
                                    rf'"{field}"\s*:\s*([^,}}]+)', item_str
                                )
                                if field_match_no_quotes:
                                    rec[field] = (
                                        field_match_no_quotes.group(1)
                                        .strip()
                                        .replace('"', "")
                                    )
                                else:
                                    rec[field] = "Not Found"
                        if rec.get("assessment_name") != "Not Found":
                            recommendations["recommendations"].append(rec)
                else:
                    print("Fallback regex parsing failed to find structure.")
                    recommendations = {"recommendations": []}

            # Limit to max_results
            if "recommendations" in recommendations:
                recommendations["recommendations"] = recommendations["recommendations"][
                    :max_results
                ]
                print(
                    f"Found {len(recommendations['recommendations'])} recommendations after parsing and filtering."
                )
            else:
                print("No 'recommendations' key found in parsed output.")
                recommendations = {"recommendations": []}

            return recommendations
        except Exception as e:
            print(f"Error processing query in recommend method: {e}")
            print(f"Raw response at time of error: {raw_response}")
            return {"error": str(e), "recommendations": []}


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
