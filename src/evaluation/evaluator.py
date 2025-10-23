"""Core evaluator that uses LLM to score design research agent outputs."""

import json
import os
from typing import Optional
from dotenv import load_dotenv

from src.schemas.responses import DesignResearchResponse
from src.schemas.evaluation_schema import EvaluationResult
from src.llm.openai_client import OpenAILLM
from src.llm.claude_client import ClaudeLLM
from src.utils.json_utils import coerce_json_object
from src.evaluation.prompts import build_evaluation_prompt

load_dotenv()


def evaluate_response(
    user_query: str,
    response: DesignResearchResponse,
    evaluator_provider: Optional[str] = None,
) -> EvaluationResult:
    """
    Evaluate a design research response using an LLM evaluator.
    
    Args:
        user_query: Original user question
        response: The agent's response to evaluate
        evaluator_provider: Which LLM to use ('GPT-5' or 'Claude Sonnet 4.5'). 
                          If None, uses EVALUATOR_LLM_PROVIDER env var or defaults to 'GPT-5'
    
    Returns:
        EvaluationResult with scores and critique
    
    Raises:
        ValueError: If evaluator provider is invalid
        Exception: If evaluation fails
    """
    # Determine which LLM to use for evaluation
    if evaluator_provider is None:
        evaluator_provider = os.getenv("EVALUATOR_LLM_PROVIDER", "openai").lower()
    
    if evaluator_provider not in ["GPT-5", "Claude Sonnet 4.5"]:
        raise ValueError(f"Invalid evaluator provider: {evaluator_provider}. Must be 'GPT-5' or 'Claude Sonnet 4.5'")
    
    # Build evaluation prompt
    prompt = build_evaluation_prompt(user_query, response)
    
    # Select LLM
    if evaluator_provider == "GPT-5":
        llm = OpenAILLM()
    else:
        llm = ClaudeLLM()
    
    # Get evaluation from LLM
    try:
        raw_response = llm.synthesize(prompt)
        
        # Parse JSON response
        eval_data = coerce_json_object(raw_response)
        
        # Validate and return
        evaluation = EvaluationResult(**eval_data)
        return evaluation
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse evaluation JSON: {e}\nRaw response: {raw_response}")
    except Exception as e:
        raise Exception(f"Evaluation failed: {e}")


def evaluate_response_stream(
    user_query: str,
    response: DesignResearchResponse,
    evaluator_provider: Optional[str] = None,
):
    """
    Stream the evaluator model output as it arrives. Yields incremental text chunks.
    Caller is responsible for assembling the final JSON and parsing.
    """
    if evaluator_provider is None:
        evaluator_provider = os.getenv("EVALUATOR_LLM_PROVIDER", "GPT-5").lower()
    if evaluator_provider not in ["GPT-5", "Claude Sonnet 4.5"]:
        raise ValueError("Invalid evaluator provider for streaming")

    prompt = build_evaluation_prompt(user_query, response)
    llm = OpenAILLM() if evaluator_provider == "GPT-5" else ClaudeLLM()
    for chunk in llm.synthesize_stream(prompt):
        yield chunk


__all__ = ["evaluate_response"]
