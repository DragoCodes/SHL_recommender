from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse

from engine2 import SHLRecommendationEngine

app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="API for recommending SHL assessments based on job requirements",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global recommendation engine instance
engine = None


class RecommendationRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

    class Config:
        schema_extra = {
            "example": {
                "query": "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for assessment(s) that can be completed in 40 minutes.",
                "max_results": 5,
            }
        }


class Assessment(BaseModel):
    assessment_name: str
    url: str
    remote_testing_support: str
    adaptive_irt_support: str
    duration: str
    test_type: str


class RecommendationResponse(BaseModel):
    recommendations: List[Assessment]


class ErrorResponse(BaseModel):
    error: str


def get_engine():
    """
    Dependency to get the recommendation engine instance.
    This ensures the engine is initialized only once.
    """
    global engine
    if engine is None:
        try:
            engine = SHLRecommendationEngine(use_local_embeddings=True)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize recommendation engine: {str(e)}",
            )
    return engine


@app.post(
    "/recommend",
    response_model=RecommendationResponse,
    responses={
        200: {"description": "Successful response", "model": RecommendationResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_recommendations(
    request: RecommendationRequest,
    engine: SHLRecommendationEngine = Depends(get_engine),
):
    """
    Get SHL assessment recommendations based on job requirements

    - **query**: Job description and requirements
    - **max_results**: Maximum number of recommendations to return
    """
    try:
        results = engine.recommend(request.query, request.max_results)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {str(e)}"
        )


@app.get(
    "/health",
    responses={
        200: {"description": "API is healthy"},
        500: {"description": "API is unhealthy", "model": ErrorResponse},
    },
)
async def health_check(engine: SHLRecommendationEngine = Depends(get_engine)):
    """
    Check if the API and recommendation engine are healthy
    """
    try:
        # Simple query to test if the engine is working
        test_query = "Test health check"
        engine.retriever.get_relevant_documents(test_query)
        return {"status": "healthy", "message": "Recommendation engine is operational"}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "api": "SHL Assessment Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "POST /recommend": "Get SHL assessment recommendations",
            "GET /health": "Check API health status",
        },
    }


if __name__ == "__main__":
    import uvicorn

    # Initialize the engine at startup
    get_engine()

    uvicorn.run(app, host="0.0.0.0", port=8080)
