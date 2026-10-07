"""
AI Routes for PlannedEducation
Provides endpoints for AI grading, test creation, and content generation
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models, schemas
from .routes_auth import get_current_user
from .ai_providers import (
    AIProviderConfig,
    get_ai_provider,
    get_teacher_ai_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Request/Response Models ──────────────────────────────────────────────────

class GradingRequest(BaseModel):
    """Request for AI grading."""
    submission_id: str
    rubric: str = Field(..., max_length=8192)
    student_response: str = Field(..., max_length=16384)
    question_text: str = Field(..., max_length=4096)
    points_possible: int = Field(..., ge=1, le=100)
    system_prompt: Optional[str] = None


class GradingResponse(BaseModel):
    """Response from AI grading."""
    score: float = Field(..., ge=0.0, le=100.0)
    feedback: str = Field(..., max_length=8192)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class TestCreationRequest(BaseModel):
    """Request for AI test creation."""
    topic: str = Field(..., max_length=512)
    grade_level: str = Field(..., max_length=64)
    num_questions: int = Field(..., ge=1, le=50)
    question_types: list[str] = Field(default=["multiple_choice", "essay", "dynamic_math"])
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")
    system_prompt: Optional[str] = None


class TestCreationResponse(BaseModel):
    """Response from AI test creation."""
    questions: list[dict]
    metadata: dict


class ContentGenerationRequest(BaseModel):
    """Request for AI content generation."""
    prompt: str = Field(..., max_length=8192)
    content_type: str = Field(..., pattern=r"^(lesson_plan|worksheet|rubric|explanation|feedback)$")
    context: Optional[str] = None
    system_prompt: Optional[str] = None


class ContentGenerationResponse(BaseModel):
    """Response from AI content generation."""
    content: str
    metadata: dict


class AICostTracking(BaseModel):
    """AI usage and cost tracking."""
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    timestamp: str


# ── Cost Tracking (Optional - for teacher visibility) ────────────────────────

# In-memory cost tracking (in production, use Redis/DB)
_ai_cost_tracking: dict[str, list[AICostTracking]] = {}


def _record_usage(user_id: str, provider: str, model: str, usage: dict, estimated_cost: float):
    """Record AI usage for cost tracking (teacher visibility only)."""
    from datetime import datetime, UTC

    entry = AICostTracking(
        provider=provider,
        model=model,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        estimated_cost_usd=estimated_cost,
        timestamp=datetime.now(UTC).isoformat(),
    )

    if user_id not in _ai_cost_tracking:
        _ai_cost_tracking[user_id] = []
    _ai_cost_tracking[user_id].append(entry)


def _estimate_cost(provider: str, model: str, usage: dict) -> float:
    """Estimate cost in USD for AI API call (for teacher visibility)."""
    # Rough estimates per 1K tokens (as of 2026)
    pricing = {
        "gemini": {"input": 0.000125, "output": 0.0005},  # Gemini 2.5 Flash
        "openrouter": {"input": 0.0005, "output": 0.0015},  # Varies by model
        "ollama": {"input": 0.0, "output": 0.0},  # Free local
        "openai-compatible": {"input": 0.001, "output": 0.003},  # GPT-4o mini approx
    }

    rates = pricing.get(provider, {"input": 0.001, "output": 0.003})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    cost = (prompt_tokens / 1000 * rates["input"]) + (completion_tokens / 1000 * rates["output"])
    return round(cost, 6)


# ── System Prompts ──────────────────────────────────────────────────────────

GRADING_SYSTEM_PROMPT = """You are an expert teacher grading student work. Your task is to evaluate the student's response against the provided rubric and question.

Guidelines:
1. Be fair, consistent, and constructive
2. Award partial credit where appropriate
3. Provide specific, actionable feedback
4. Consider the student's reasoning, not just the final answer
5. Return a score (0-100) and detailed feedback

Output format (JSON):
{
  "score": <number 0-100>,
  "feedback": "<detailed feedback>",
  "confidence": <number 0-1>,
  "reasoning": "<explanation of grading decision>"
}"""

TEST_CREATION_SYSTEM_PROMPT = """You are an expert teacher creating educational assessments. Generate high-quality test questions based on the given topic and parameters.

Guidelines:
1. Questions should be age-appropriate and aligned with the grade level
2. Mix question types as requested
3. Include clear correct answers and rubrics
4. For dynamic math, use variable placeholders like [rand:1-10]
5. Ensure questions test understanding, not just memorization

Output format (JSON):
{
  "questions": [
    {
      "question_type": "multiple_choice|essay|dynamic_math",
      "text": "<question text>",
      "options_json": "[...]" (for multiple_choice only),
      "correct_answer": "<answer>",
      "rubric": "<grading rubric>",
      "points": <1-100>
    }
  ],
  "metadata": {
    "topic": "<topic>",
    "grade_level": "<grade>",
    "difficulty": "<difficulty>",
    "total_points": <sum>
  }
}"""

CONTENT_GENERATION_SYSTEM_PROMPT = """You are an expert educational content creator. Generate high-quality educational content based on the request.

Guidelines:
1. Content should be pedagogically sound and age-appropriate
2. Use clear, accessible language
3. Include examples and explanations where helpful
4. Structure content logically with headings/sections

Output format (JSON):
{
  "content": "<generated content>",
  "metadata": {
    "content_type": "<type>",
    "word_count": <number>,
    "estimated_reading_time_minutes": <number>
  }
}"""


# ── Output Validation ────────────────────────────────────────────────────────

GRADING_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "feedback": {"type": "string", "maxLength": 8192},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string", "maxLength": 4096}
    },
    "required": ["score", "feedback", "confidence"],
    "additionalProperties": False
}

TEST_CREATION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_type": {"type": "string", "enum": ["multiple_choice", "essay", "dynamic_math"]},
                    "text": {"type": "string", "maxLength": 4096},
                    "options_json": {"type": "string"},
                    "correct_answer": {"type": "string", "maxLength": 2048},
                    "rubric": {"type": "string", "maxLength": 4096},
                    "points": {"type": "integer", "minimum": 1, "maximum": 100}
                },
                "required": ["question_type", "text", "correct_answer", "rubric", "points"]
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "grade_level": {"type": "string"},
                "difficulty": {"type": "string"},
                "total_points": {"type": "integer"}
            },
            "required": ["topic", "grade_level", "difficulty", "total_points"]
        }
    },
    "required": ["questions", "metadata"],
    "additionalProperties": False
}

CONTENT_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "content_type": {"type": "string"},
                "word_count": {"type": "integer"},
                "estimated_reading_time_minutes": {"type": "integer"}
            },
            "required": ["content_type", "word_count", "estimated_reading_time_minutes"]
        }
    },
    "required": ["content", "metadata"],
    "additionalProperties": False
}


def _validate_json_response(response: str, schema: dict) -> dict:
    """Validate AI response against JSON schema."""
    try:
        data = json.loads(response)
        # Basic validation - in production use jsonschema library
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {e}"
        )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/grade", response_model=GradingResponse)
async def ai_grade(
    request: GradingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Grade a student response using AI.
    Requires teacher to have AI provider configured.
    """
    # Get teacher's AI provider
    provider = await get_teacher_ai_provider(current_user, db)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Set up your AI key in settings."
        )

    # Build grading prompt
    prompt = f"""Question: {request.question_text}
Points Possible: {request.points_possible}
Rubric: {request.rubric}

Student Response:
{request.student_response}

Grade this response according to the rubric."""

    # Generate grade
    response = await provider.generate_structured(
        prompt=prompt,
        schema=GRADING_SCHEMA,
        system_prompt=request.system_prompt or GRADING_SYSTEM_PROMPT,
        temperature=0.3,  # Lower temperature for consistent grading
    )

    if response.error:
        raise HTTPException(status_code=500, detail=f"AI grading failed: {response.error}")

    # Validate response
    try:
        result = _validate_json_response(response.content, GRADING_SCHEMA)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid AI response format: {e}")

    # Track usage for cost visibility (optional)
    estimated_cost = _estimate_cost(response.provider or "unknown", response.model or "unknown", response.usage or {})
    _record_usage(current_user.id, response.provider or "unknown", response.model or "unknown",
                  response.usage or {}, estimated_cost)

    return GradingResponse(
        score=result["score"],
        feedback=result["feedback"],
        confidence=result["confidence"],
        reasoning=result.get("reasoning")
    )


@router.post("/create-test", response_model=TestCreationResponse)
async def ai_create_test(
    request: TestCreationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Create a test using AI.
    Requires teacher to have AI provider configured.
    """
    # Get teacher's AI provider
    provider = await get_teacher_ai_provider(current_user, db)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Set up your AI key in settings."
        )

    # Build test creation prompt
    prompt = f"""Create a test with the following specifications:
Topic: {request.topic}
Grade Level: {request.grade_level}
Number of Questions: {request.num_questions}
Question Types: {', '.join(request.question_types)}
Difficulty: {request.difficulty}

Generate {request.num_questions} questions with a mix of the specified types.
For dynamic_math questions, use [rand:min-max] placeholders for variable numbers.
For multiple_choice, provide 4 options with one correct answer.
Include rubrics for all questions."""

    # Generate test
    response = await provider.generate_structured(
        prompt=prompt,
        schema=TEST_CREATION_SCHEMA,
        system_prompt=request.system_prompt or TEST_CREATION_SYSTEM_PROMPT,
        temperature=0.7,
    )

    if response.error:
        raise HTTPException(status_code=500, detail=f"AI test creation failed: {response.error}")

    # Validate response
    try:
        result = _validate_json_response(response.content, TEST_CREATION_SCHEMA)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid AI response format: {e}")

    # Track usage for cost visibility (optional)
    estimated_cost = _estimate_cost(response.provider or "unknown", response.model or "unknown", response.usage or {})
    _record_usage(current_user.id, response.provider or "unknown", response.model or "unknown",
                  response.usage or {}, estimated_cost)

    return TestCreationResponse(
        questions=result["questions"],
        metadata=result["metadata"]
    )


@router.post("/generate-content", response_model=ContentGenerationResponse)
async def ai_generate_content(
    request: ContentGenerationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Generate educational content using AI.
    Requires teacher to have AI provider configured.
    """
    # Get teacher's AI provider
    provider = await get_teacher_ai_provider(current_user, db)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Set up your AI key in settings."
        )

    # Build content generation prompt
    prompt = f"""Generate {request.content_type} content:
Prompt: {request.prompt}
Context: {request.context or 'None provided'}"""

    # Generate content
    response = await provider.generate_structured(
        prompt=prompt,
        schema=CONTENT_GENERATION_SCHEMA,
        system_prompt=request.system_prompt or CONTENT_GENERATION_SYSTEM_PROMPT,
        temperature=0.7,
    )

    if response.error:
        raise HTTPException(status_code=500, detail=f"AI content generation failed: {response.error}")

    # Validate response
    try:
        result = _validate_json_response(response.content, CONTENT_GENERATION_SCHEMA)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid AI response format: {e}")

    # Track usage for cost visibility (optional)
    estimated_cost = _estimate_cost(response.provider or "unknown", response.model or "unknown", response.usage or {})
    _record_usage(current_user.id, response.provider or "unknown", response.model or "unknown",
                  response.usage or {}, estimated_cost)

    return ContentGenerationResponse(
        content=result["content"],
        metadata=result["metadata"]
    )


@router.get("/usage", response_model=list[AICostTracking])
async def get_ai_usage(
    current_user: models.User = Depends(get_current_user),
):
    """Get AI usage and cost tracking for current teacher."""
    return _ai_cost_tracking.get(current_user.id, [])


@router.get("/usage/summary")
async def get_ai_usage_summary(
    current_user: models.User = Depends(get_current_user),
):
    """Get AI usage summary for current teacher."""
    from datetime import datetime, UTC

    today = datetime.now(UTC).date().isoformat()
    entries = _ai_cost_tracking.get(current_user.id, [])

    today_entries = [e for e in entries if e.timestamp.startswith(today)]
    total_cost = sum(e.estimated_cost_usd for e in today_entries)
    total_calls = len(today_entries)
    total_prompt_tokens = sum(e.prompt_tokens for e in today_entries)
    total_completion_tokens = sum(e.completion_tokens for e in today_entries)

    by_provider = {}
    for entry in today_entries:
        if entry.provider not in by_provider:
            by_provider[entry.provider] = {"calls": 0, "cost": 0.0, "tokens": 0}
        by_provider[entry.provider]["calls"] += 1
        by_provider[entry.provider]["cost"] += entry.estimated_cost_usd
        by_provider[entry.provider]["tokens"] += entry.prompt_tokens + entry.completion_tokens

    return {
        "date": today,
        "total_calls": total_calls,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "daily_limit_usd": MAX_DAILY_COST_USD,
        "remaining_budget_usd": round(MAX_DAILY_COST_USD - total_cost, 6),
        "by_provider": by_provider,
    }