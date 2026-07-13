import logging
from typing import Dict, Any
from app.celery_app import celery_app
from app.llm_engine import generate_interpretation_answer
from app.storage.database import get_service_client, update_prashna_chart

logger = logging.getLogger(__name__)

@celery_app.task(name="generate_reading_task")
def generate_reading_task(chart_id: str, chart: Dict[str, Any], interpretation: Dict[str, Any]) -> str:
    """
    Background task to run the Map-Reduce LLM pipeline.
    This prevents the API from blocking while OpenAI/Gemini generates the 1000-word response.
    """
    logger.info(f"Starting background generation for chart {chart_id}")
    try:
        # Run the heavy LLM Map-Reduce pipeline
        answer = generate_interpretation_answer(chart, interpretation, chart_id=chart_id)
        interpretation["answer"] = answer
        chart["interpretation"] = interpretation
        
        # Update Supabase with the final generated text
        update_prashna_chart(get_service_client(), chart_id, chart)
        logger.info(f"Successfully generated and saved reading for chart {chart_id}")
        return "SUCCESS"
    except Exception as e:
        logger.error(f"Failed to generate reading for chart {chart_id}: {str(e)}")
        # Ideally, we would save the error state to the database here so the frontend knows it failed
        raise e
