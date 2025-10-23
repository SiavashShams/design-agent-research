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

load_dotenv()


def _build_evaluation_prompt(
    user_query: str,
    response: DesignResearchResponse,
) -> str:
    """
    Build a detailed prompt for the LLM evaluator.
    
    This prompt instructs the LLM to score the response across multiple dimensions
    based on the assignment criteria.
    """
    
    # Convert response to dict for easier inclusion in prompt
    response_dict = response.model_dump(mode="json")
    response_json = json.dumps(response_dict, indent=2)
    
    # Get evaluation schema
    schema = EvaluationResult.model_json_schema()
    schema_json = json.dumps(schema, separators=(",", ":"))
    
    prompt = f"""You are an expert evaluator for a Design Research AI Agent. Your task is to critically evaluate the agent's response to a user query based on specific criteria from the assignment rubric.

# USER QUERY
{user_query}

# AGENT RESPONSE
{response_json}

# EVALUATION CRITERIA

Evaluate the response across these dimensions (each scored 0-10):

1. **Relevance (0-10)**: 
   - Are the search results and recommendations directly relevant to the query?
   - Does it understand the design context?
   - For pattern queries: Does it address when/why to use patterns?
   - For accessibility queries: Does it provide specific WCAG guidance?
   - For inspiration queries: Are examples truly inspiring and relevant?
   - For feasibility queries: Does it assess current browser support and performance?

2. **Synthesis Quality (0-10)**:
   - Does it provide ORIGINAL INSIGHTS rather than copy-paste summaries?
   - Does it synthesize information across multiple sources?
   - Does it add NEW INFORMATION or perspectives not obvious from sources alone?
   - Does it demonstrate deep understanding rather than surface-level aggregation?
   - CRITICAL: Deduct points heavily if response appears to be copied/summarized text

3. **Completeness (0-10)**:
   - Does it fully answer the question asked?
   - Are all required sections present (summary, best_practices, examples, considerations, sources)?
   - Is the summary 2-3 sentences?
   - Are there 5-10 actionable best practices?
   - Are there 3-6 relevant examples with working URLs?
   - Are all 4 consideration categories covered (tradeoffs, accessibility, performance, browser_support)?

4. **Actionability (0-10)**:
   - Is the information specific and actionable for designers?
   - Is the detail level appropriate (not too vague, not too technical)?
   - Can a designer implement these recommendations?
   - Are best practices concrete and not generic advice?

5. **Citations (0-10)**:
   - Are sources properly cited?
   - Do citations use [n] bracket notation correctly?
   - Are all cited sources listed in the sources array?
   - Are sources from authoritative design resources?
   - Are claims that could change or be disputed properly cited?

6. **Accessibility (0-10)**:
   - Are accessibility considerations comprehensive?
   - Are exact WCAG 2.2 criterion IDs cited where relevant?
   - Does it cover keyboard navigation, screen readers, color contrast?
   - Is accessibility integrated throughout, not just mentioned?

7. **Examples Quality (0-10)**:
   - Are examples real and from reputable sources?
   - Do URLs work and point to relevant examples?
   - Are descriptions helpful and specific?
   - Are visual references (images) included where appropriate?
   - Do examples demonstrate the concepts being discussed?

# OUTPUT FORMAT

You must return a SINGLE VALID JSON object matching the EvaluationResult schema below. No markdown, no code fences, just pure JSON.

Schema:
{schema_json}

# SCORING GUIDANCE

- Be critical but fair
- Score 0-3: Poor (fails to meet basic requirements)
- Score 4-6: Acceptable (meets requirements but has significant issues)
- Score 7-8: Good (solid work with minor issues)
- Score 9-10: Excellent (exceeds expectations)

Overall score is calculated as weighted average:
- Relevance: 20%
- Synthesis Quality: 25%
- Completeness: 15%
- Actionability: 15%
- Citations: 10%
- Accessibility: 10%
- Examples Quality: 5%

# IMPORTANT NOTES

- Be specific in your critique - cite examples from the response
- In "weaknesses", point to actual issues you see
- In "strengths", highlight what was done well
- In "recommendations", give actionable advice to improve
- Consider the query type when evaluating appropriateness
- Heavily penalize copy-paste style responses (common failure mode)
- Reward original synthesis and insights
- Check if response truly answers what was asked

Now evaluate the response and return your evaluation as valid JSON."""

    return prompt


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
    prompt = _build_evaluation_prompt(user_query, response)
    
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

    prompt = _build_evaluation_prompt(user_query, response)
    llm = OpenAILLM() if evaluator_provider == "GPT-5" else ClaudeLLM()
    for chunk in llm.synthesize_stream(prompt):
        yield chunk


__all__ = ["evaluate_response"]
