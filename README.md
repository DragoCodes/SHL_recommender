# SHL Assessment Recommendation Engine

A RAG-based system to recommend SHL assessments, scraping data from the SHL catalog, indexing with FAISS, and serving via FastAPI on Google Cloud Run, with a Streamlit frontend option.

## Overview
- **Purpose**: Recommends SHL assessments based on job queries.
- **Pipeline**:
  - Scrape: `scraper.py` → `shl_catalog_detailed.csv`.
  - Index: `prep.py` → `faiss_index/`.
  - RAG: `engine.py` with Gemini API.
  - API: `api.py` (FastAPI).
  - Frontend: `app.py` (Streamlit).

## URLs
1. **Demo**: [https://shl-recommendation-abc123-uc.a.run.app/docs](https://shl-recommendation-1050995543702.us-central1.run.app/docs) - Swagger UI.
2. **API**: [https://shl-recommendation-abc123-uc.a.run.app/recommend](https://shl-recommendation-1050995543702.us-central1.run.app/recommend) - POST JSON queries.
3. **Code**: [https://github.com/drago-codes/shl-recommendation](https://github.com/DragoCodes/SHL_recommender) - This repo.

## Setup
1. **Prerequisites**:
   - Python 3.12, Docker, Google Cloud SDK, Gemini API Key.

2. **Scrape Data**:
   ```bash
   uv run python scraper.py
