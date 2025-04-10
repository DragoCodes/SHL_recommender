import os

import pandas as pd
import torch
from dotenv import load_dotenv

# Updated imports to avoid deprecation warnings
from langchain_community.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()  # Load environment variables from .env file


def prepare_data(
    csv_file="transformed_data.csv",
    use_local_embeddings=True,
):
    """
    Prepare the SHL assessment data and create a vector store
    """
    print("Loading SHL assessment data...")
    # Load the CSV data
    df = pd.read_csv(csv_file)

    # Clean and prepare the data
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("")
        else:
            df[col] = df[col].fillna(0)

    # Convert boolean strings to actual booleans if needed
    if "adaptive_support" in df.columns:
        df["adaptive_support"] = df["adaptive_support"].astype(str)
    if "remote_support" in df.columns:
        df["remote_support"] = df["remote_support"].astype(str)

    # Extract title from URL
    df["title"] = df["url"].apply(
        lambda url: url.split("/")[-2].replace("-", " ").title()
    )

    # Create rich text for embedding
    df["combined_text"] = df.apply(
        lambda row: f"Title: {row['title']}\n"
        f"Test Type: {row['test_type']}\n"
        f"Description: {row['description']}\n"
        f"Assessment Length: {row['duration']} minutes\n"
        f"Remote Testing Support: {row['remote_support']}\n"
        f"Adaptive Support: {row['adaptive_support']}\n"
        f"URL: {row['url']}",
        axis=1,
    )

    # Create the embedding model based on preference (local vs OpenAI)
    if use_local_embeddings:
        print("Using local HuggingFace embeddings (free, no API key needed)...")
        # For M1 Mac, choose a smaller model that will work efficiently with 16GB RAM
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",  # Smaller model good for M1 Macs
            model_kwargs={
                "device": "mps" if torch.backends.mps.is_available() else "cpu"
            },
        )
    else:
        # Only try OpenAI if specifically requested
        print("Using OpenAI embeddings (requires API key and quota)...")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        embeddings = OpenAIEmbeddings()

    # Create FAISS index from the texts
    texts = df["combined_text"].tolist()
    metadatas = df.to_dict("records")

    print(f"Creating vector store from {len(texts)} documents...")
    # Create and save the vector store
    vectorstore = FAISS.from_texts(
        texts=texts, embedding=embeddings, metadatas=metadatas
    )

    # Save the vectorstore to disk
    vectorstore.save_local("faiss_index")

    print(f"Processed {len(df)} SHL assessments")
    print("Vector store created and saved to 'faiss_index'")

    return vectorstore


if __name__ == "__main__":
    prepare_data(
        use_local_embeddings=True
    )  # Set to False if you want to use OpenAI (with valid API key)
