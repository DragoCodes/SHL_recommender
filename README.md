# SHL Assessment Recommendation Engine

A Retrieval-Augmented Generation (RAG) system designed to recommend relevant SHL assessments based on user queries (e.g., job descriptions or required skills). This project scrapes assessment data from the SHL catalog, indexes it using FAISS for efficient similarity search, utilizes a Google Gemini LLM for generation, and serves recommendations via a FastAPI backend deployed on Google Cloud Run. An optional Streamlit frontend is included for local demonstration.

## Overview

The system follows this pipeline:

1.  **Scrape (`scraper.py`)**: Extracts assessment data from the SHL catalog.
2.  **CSV Output**: Stores the scraped data temporarily.
3.  **Index (`prep.py`)**: Processes the data and creates a FAISS vector index for efficient retrieval.
4.  **RAG (`engine2.py`)**: Combines retrieved assessments (using the FAISS index) with a Large Language Model (Gemini) to generate relevant recommendations based on the user query.
5.  **API (`api.py`)**: Exposes the recommendation logic via a FastAPI endpoint.
6.  **Frontend (`app.py`)**: Provides an optional Streamlit interface for interaction (run locally).
7.  **DockerFile (`Dockerfile`)**: Dockerfile for building and serving FastAPI app.

## URLs

*   **Live Demo (API Docs)**: [https://shl-recommendation-abc123-uc.a.run.app/docs](https://shl-recommendation-abc123-uc.a.run.app/docs)
*   **API Endpoint**: [https://shl-recommendation-abc123-uc.a.run.app/recommend](https://shl-recommendation-abc123-uc.a.run.app/recommend)
*   **Source Code**: [https://github.com/drago-codes/shl-recommendation](https://github.com/drago-codes/shl-recommendation)

## Setup and Installation

Follow these steps to set up and run the project locally or deploy it.

### Prerequisites

*   Python 3.12 or higher
*   [Docker](https://docs.docker.com/get-docker/) installed
*   [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured (`gcloud init`)
*   [uv](https://github.com/astral-sh/uv) Python package manager
*   A Google Gemini API Key (obtainable from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/drago-codes/shl-recommendation.git
    cd shl-recommendation
    ```

2.  **Install dependencies:**
    ```bash
    # Using uv
    uv sync
    ```

3.  **Scrape Assessment Data:**
    *(This step generates the initial data CSV file)*
    ```bash
    uv run python scraper.py
    ```

4.  **Prepare FAISS Index:**
    *(This step processes the CSV and creates the `faiss_index` directory)*
    ```bash
    uv run python prep.py
    ```

5.  **Build and Run Docker Container (API):**
    *(This runs the FastAPI application locally)*
    ```bash
    # Set your Gemini API Key environment variable (replace your_key)
    export GOOGLE_API_KEY="your_key"

    # Build the Docker image
    docker build -t shl-recommendation .

    # Run the Docker container
    docker run -p 8080:8080 --env GOOGLE_API_KEY="$GOOGLE_API_KEY" shl-recommendation
    ```
    *Note: On Windows Command Prompt use `set GOOGLE_API_KEY=your_key` and `%GOOGLE_API_KEY%` in the docker run command.*

6.  **Test the Local API:**
    *(Verify the API is running)*
    ```bash
    curl http://localhost:8080/health
    # Expected output: {"status":"ok"}
    ```

7.  **Run Streamlit Frontend (Optional, Local):**
    *(Requires dependencies installed locally, not just in Docker)*
    ```bash
    # Ensure GOOGLE_API_KEY is set in your environment
    export GOOGLE_API_KEY="your_key"
    uv run streamlit run app.py
    ```
    Access the Streamlit app at `http://localhost:8501`.

## Deployment to Google Cloud Run

1.  **Initialize Google Cloud SDK (if not done already):**
    ```bash
    gcloud init
    ```
    Follow the prompts to select your Google Cloud project. Let's assume your Project ID is `<YOUR_GCP_PROJECT_ID>`.

2.  **Enable Required APIs:**
    ```bash
    gcloud services enable run.googleapis.com containerregistry.googleapis.com artifactregistry.googleapis.com
    ```
    *(Note: Container Registry (gcr.io) is being replaced by Artifact Registry. Using Artifact Registry is recommended for new projects, but the example uses gcr.io. Adjust if necessary.)*

3.  **Configure Docker Authentication:**
    ```bash
    gcloud auth configure-docker gcr.io
    # Or configure for Artifact Registry if using that
    # gcloud auth configure-docker <REGION>-docker.pkg.dev
    ```

4.  **Tag the Docker Image:**
    ```bash
    docker tag shl-recommendation gcr.io/<YOUR_GCP_PROJECT_ID>/shl-recommendation:latest
    ```
    *(Replace `<YOUR_GCP_PROJECT_ID>` with your actual Google Cloud Project ID)*

5.  **Push the Docker Image to Google Container Registry (GCR):**
    ```bash
    docker push gcr.io/<YOUR_GCP_PROJECT_ID>/shl-recommendation:latest
    ```

6.  **Deploy to Google Cloud Run:**
    ```bash
    # Replace <YOUR_GCP_PROJECT_ID> and your_key
    gcloud run deploy shl-recommendation \
        --image gcr.io/<YOUR_GCP_PROJECT_ID>/shl-recommendation:latest \
        --platform managed \
        --region us-central1 \
        --memory 1Gi \
        --allow-unauthenticated \
        --set-env-vars "GOOGLE_API_KEY=your_key"
    ```
    *   `--allow-unauthenticated` makes the service publicly accessible. Remove if authentication is required.
    *   Adjust `--region`, `--memory`, and other flags as needed.
    *   The command will output the deployed Service URL (similar to the one in the URLs section).

## Usage

### API Call

Make POST requests to the `/recommend` endpoint of your deployed service (or `http://localhost:8080/recommend` if running locally).

**Example using `curl`:**

```bash
curl -X POST https://shl-recommendation-abc123-uc.a.run.app/recommend \
     -H "Content-Type: application/json" \
     -d '{
           "query": "Entry-level software engineer skilled in Python and teamwork",
           "max_results": 3
         }'# SHL Assessment Recommendation Engine
