from typing import List

from engine2 import SHLRecommendationEngine
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

    class Config:
        schema_extra = {
            "example": {
                "query": "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for assessment(s) that can be completed in 40 minutes."
            }
        }


class Assessment(BaseModel):
    url: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]


class RecommendationResponse(BaseModel):
    recommended_assessments: List[Assessment]


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
)
async def get_recommendations(
    request: RecommendationRequest,
    engine: SHLRecommendationEngine = Depends(get_engine),
):
    """
    Get SHL assessment recommendations based on job requirements or natural language query.
    """
    try:
        # Set max_results to 10 as per requirements
        results = engine.recommend(request.query, max_results=10)

        # Ensure the response follows the required format
        # If the engine returns a different format, transform it here
        if "recommended_assessments" not in results:
            if "recommendations" in results:
                # Handle case where engine returns with "recommendations" key
                assessments = results["recommendations"]
                formatted_assessments = []

                for assessment in assessments:
                    formatted_assessment = {
                        "url": assessment.get("url", ""),
                        "adaptive_support": assessment.get(
                            "adaptive_irt_support", "No"
                        ),
                        "description": assessment.get("assessment_name", ""),
                        "duration": int(assessment.get("duration", 0))
                        if assessment.get("duration")
                        else 0,
                        "remote_support": assessment.get(
                            "remote_testing_support", "No"
                        ),
                        "test_type": [assessment.get("test_type", "Unknown")]
                        if isinstance(assessment.get("test_type"), str)
                        else assessment.get("test_type", ["Unknown"]),
                    }
                    formatted_assessments.append(formatted_assessment)

                return {"recommended_assessments": formatted_assessments}
            else:
                # Handle other cases
                return {"recommended_assessments": []}

        return results
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Initialize the engine at startup
    get_engine()

    uvicorn.run(app, host="0.0.0.0", port=8080)
