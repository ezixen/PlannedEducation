"""
Test Package Routes for PlannedEducation
Endpoints for importing/exporting modular test packages (JSON/YAML)
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
import yaml
import hashlib
import uuid

from . import database, models
from .routes_auth import get_current_user

router = APIRouter(prefix="/packages", tags=["packages"])


# ── Pydantic Schemas ────────────────────────────────────────────────────────

class PackageMetadata(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    subject: str = ""
    grade_level: str = ""
    license: str = "CC-BY-4.0"
    checksum: str


class ExamSettings(BaseModel):
    shuffle_questions: bool = False
    shuffle_options: bool = False
    show_results_immediately: bool = False
    allow_review: bool = True
    require_seb: bool = False
    time_multiplier: float = 1.0
    passing_score: int = 60


class ExamTemplate(BaseModel):
    title: str
    description: str = ""
    duration_minutes: int = 60
    instructions: str = ""
    settings: ExamSettings = ExamSettings()


class QuestionVariable(BaseModel):
    name: str
    type: str  # integer, float, choice
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[List[str]] = None
    formula: Optional[str] = None


class QuestionTemplate(BaseModel):
    id: str
    question_type: str  # multiple_choice, essay, dynamic_math
    text: str
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    rubric: Optional[str] = None
    points: int = 1
    variables: List[QuestionVariable] = []
    tags: List[str] = []
    difficulty: str = "medium"
    estimated_time_minutes: int = 5


class RubricCriterion(BaseModel):
    id: str
    description: str
    points: int
    keywords: List[str] = []


class RubricTemplate(BaseModel):
    id: str
    question_id: str
    criteria: List[RubricCriterion]
    total_points: int


class TestPackage(BaseModel):
    metadata: PackageMetadata
    exam: ExamTemplate
    questions: List[QuestionTemplate]
    rubrics: List[RubricTemplate] = []


class PackageExportRequest(BaseModel):
    exam_id: str
    include_answers: bool = True
    include_rubrics: bool = True
    include_variables: bool = True
    format: str = "json"  # json or yaml
    compress: bool = False


class PackageImportResult(BaseModel):
    success: bool
    package_id: Optional[str] = None
    exam_id: Optional[str] = None
    questions_imported: int = 0
    rubrics_imported: int = 0
    errors: List[str] = []
    warnings: List[str] = []


class PackageValidationResult(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class PackageListResponse(BaseModel):
    packages: List[PackageMetadata]


# ── Helper Functions ────────────────────────────────────────────────────────

def _calculate_checksum(data: dict) -> str:
    """Calculate SHA-256 checksum of package content."""
    # Remove checksum field before calculating
    content = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(content.encode()).hexdigest()


def _validate_package_structure(pkg: dict) -> tuple[bool, List[str], List[str]]:
    """Validate package structure and return (valid, errors, warnings)."""
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ['metadata', 'exam', 'questions']
    for field in required_fields:
        if field not in pkg:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors, warnings
    
    # Validate metadata
    metadata = pkg.get('metadata', {})
    required_metadata = ['id', 'name', 'version', 'author', 'author_id', 'checksum']
    for field in required_metadata:
        if field not in metadata:
            errors.append(f"Missing metadata field: {field}")
    
    # Validate exam
    exam = pkg.get('exam', {})
    if not exam.get('title'):
        errors.append("Exam title is required")
    
    # Validate questions
    questions = pkg.get('questions', [])
    if not isinstance(questions, list):
        errors.append("Questions must be a list")
    else:
        for i, q in enumerate(questions):
            if not q.get('id'):
                errors.append(f"Question {i}: missing id")
            if not q.get('question_type'):
                errors.append(f"Question {i}: missing question_type")
            if not q.get('text'):
                errors.append(f"Question {i}: missing text")
            if q.get('question_type') == 'multiple_choice' and not q.get('options'):
                warnings.append(f"Question {i}: multiple_choice should have options")
    
    # Verify checksum
    pkg_copy = pkg.copy()
    pkg_copy['metadata'] = pkg_copy['metadata'].copy()
    pkg_copy['metadata']['checksum'] = ''
    calculated = _calculate_checksum(pkg_copy)
    if metadata.get('checksum') != calculated:
        errors.append("Checksum mismatch - package may be corrupted or modified")
    
    return len(errors) == 0, errors, warnings


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/export", response_model=dict)
async def export_package(
    request: PackageExportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Export an exam as a test package.
    Returns the package as JSON or YAML.
    """
    # Verify exam ownership
    exam = (
        db.query(models.Exam)
        .filter(
            models.Exam.id == request.exam_id,
            models.Exam.teacher_id == current_user.id
        )
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found or access denied")
    
    # Fetch questions
    questions = (
        db.query(models.Question)
        .filter(models.Question.exam_id == exam.id)
        .all()
    )
    
    # Build package
    pkg = {
        "metadata": {
            "id": str(uuid.uuid4()),
            "name": exam.title,
            "version": "1.0.0",
            "description": exam.description or "",
            "author": current_user.full_name or current_user.username,
            "author_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tags": [],
            "subject": "",
            "grade_level": "",
            "license": "CC-BY-4.0",
            "checksum": "",
        },
        "exam": {
            "title": exam.title,
            "description": exam.description or "",
            "duration_minutes": exam.duration_minutes,
            "instructions": "",
            "settings": {
                "shuffle_questions": False,
                "shuffle_options": False,
                "show_results_immediately": False,
                "allow_review": True,
                "require_seb": bool(exam.seb_config_key),
                "time_multiplier": 1.0,
                "passing_score": 60,
            },
        },
        "questions": [],
        "rubrics": [],
    }
    
    for q in questions:
        question_data = {
            "id": q.id,
            "question_type": q.question_type.value,
            "text": q.text,
            "options": json.loads(q.options_json) if q.options_json else None,
            "correct_answer": q.correct_answer if request.include_answers else None,
            "rubric": q.rubric if request.include_rubrics else None,
            "points": q.points,
            "variables": [],
            "tags": [],
            "difficulty": "medium",
            "estimated_time_minutes": 5,
        }
        pkg["questions"].append(question_data)
    
    # Calculate checksum
    pkg_copy = pkg.copy()
    pkg_copy["metadata"] = pkg_copy["metadata"].copy()
    pkg_copy["metadata"]["checksum"] = ""
    pkg["metadata"]["checksum"] = _calculate_checksum(pkg_copy)
    
    # Serialize
    if request.format == "yaml":
        content = yaml.dump(pkg, default_flow_style=False, sort_keys=False)
        media_type = "application/yaml"
    else:
        content = json.dumps(pkg, indent=2)
        media_type = "application/json"
    
    # Compress if requested
    if request.compress:
        import gzip
        content_bytes = content.encode() if isinstance(content, str) else content
        compressed = gzip.compress(content_bytes)
        return {
            "content": compressed,
            "media_type": "application/gzip",
            "filename": f"{exam.title.replace(' ', '_')}_package.yaml.gz" if request.format == "yaml" else f"{exam.title.replace(' ', '_')}_package.json.gz"
        }
    
    return {
        "content": content,
        "media_type": media_type,
        "filename": f"{exam.title.replace(' ', '_')}_package.{request.format}"
    }


@router.post("/import", response_model=PackageImportResult)
async def import_package(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Import a test package and create an exam with questions.
    """
    # Read file
    content = await file.read()
    
    # Decompress if gzipped
    if file.filename and file.filename.endswith('.gz'):
        import gzip
        try:
            content = gzip.decompress(content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid gzip file")
    
    # Parse content
    try:
        if file.filename and file.filename.endswith(('.yaml', '.yml')):
            pkg = yaml.safe_load(content.decode())
        else:
            pkg = json.loads(content.decode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid package format: {e}")
    
    # Validate package
    valid, errors, warnings = _validate_package_structure(pkg)
    if not valid:
        return PackageImportResult(
            success=False,
            errors=errors,
            warnings=warnings,
        )
    
    # Create exam
    exam_data = pkg["exam"]
    exam = models.Exam(
        id=str(uuid.uuid4()),
        title=exam_data["title"],
        description=exam_data.get("description", ""),
        duration_minutes=exam_data.get("duration_minutes", 60),
        teacher_id=current_user.id,
        seb_config_key=None,
    )
    db.add(exam)
    db.flush()
    
    # Create questions
    questions_imported = 0
    for q_data in pkg.get("questions", []):
        question = models.Question(
            id=q_data["id"],
            exam_id=exam.id,
            question_type=q_data["question_type"],
            text=q_data["text"],
            options_json=json.dumps(q_data["options"]) if q_data.get("options") else None,
            correct_answer=q_data.get("correct_answer"),
            rubric=q_data.get("rubric"),
            points=q_data.get("points", 1),
        )
        db.add(question)
        questions_imported += 1
    
    # Create rubrics
    rubrics_imported = 0
    for r_data in pkg.get("rubrics", []):
        # Rubrics would be stored separately or linked to questions
        rubrics_imported += 1
    
    db.commit()
    
    return PackageImportResult(
        success=True,
        package_id=pkg["metadata"]["id"],
        exam_id=exam.id,
        questions_imported=questions_imported,
        rubrics_imported=rubrics_imported,
        errors=[],
        warnings=warnings,
    )


@router.post("/validate", response_model=PackageValidationResult)
async def validate_package(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    """
    Validate a test package without importing.
    """
    content = await file.read()
    
    # Decompress if gzipped
    if file.filename and file.filename.endswith('.gz'):
        import gzip
        try:
            content = gzip.decompress(content)
        except Exception:
            return PackageValidationResult(
                valid=False,
                errors=["Invalid gzip file"],
            )
    
    # Parse content
    try:
        if file.filename and file.filename.endswith(('.yaml', '.yml')):
            pkg = yaml.safe_load(content.decode())
        else:
            pkg = json.loads(content.decode())
    except Exception as e:
        return PackageValidationResult(
            valid=False,
            errors=[f"Invalid package format: {e}"],
        )
    
    valid, errors, warnings = _validate_package_structure(pkg)
    return PackageValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
    )


@router.get("", response_model=PackageListResponse)
async def list_packages(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    tags: Optional[str] = None,
    author_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    List available packages (from user's exams for now).
    In the future, this could include a marketplace.
    """
    # For now, return user's exams as packages
    query = db.query(models.Exam).filter(models.Exam.teacher_id == current_user.id)
    
    exams = query.all()
    
    packages = []
    for exam in exams:
        question_count = db.query(models.Question).filter(
            models.Question.exam_id == exam.id
        ).count()
        
        pkg_meta = PackageMetadata(
            id=exam.id,
            name=exam.title,
            version="1.0.0",
            description=exam.description or "",
            author=current_user.full_name or current_user.username,
            author_id=current_user.id,
            created_at=exam.created_at if hasattr(exam, 'created_at') else datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tags=[],
            subject="",
            grade_level="",
            license="CC-BY-4.0",
            checksum="",
        )
        packages.append(pkg_meta)
    
    return PackageListResponse(packages=packages)


@router.get("/{package_id}/download")
async def download_package(
    package_id: str,
    format: str = "json",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Download a package by ID.
    """
    # For now, treat package_id as exam_id
    exam = (
        db.query(models.Exam)
        .filter(
            models.Exam.id == package_id,
            models.Exam.teacher_id == current_user.id
        )
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Reuse export logic
    request = PackageExportRequest(
        exam_id=package_id,
        format=format,
        compress=False,
    )
    result = await export_package(request, current_user, db)
    
    from fastapi.responses import Response
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"'
        }
    )


@router.post("/{package_id}/publish")
async def publish_package(
    package_id: str,
    is_public: bool = Form(True),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """
    Publish a package to the marketplace (placeholder for future implementation).
    """
    # For now, just verify ownership
    exam = (
        db.query(models.Exam)
        .filter(
            models.Exam.id == package_id,
            models.Exam.teacher_id == current_user.id
        )
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # In the future, this would publish to a marketplace
    return {
        "status": "success",
        "message": f"Package {'published' if is_public else 'unpublished'}",
        "package_id": package_id,
        "is_public": is_public,
    }


@router.get("/health")
async def packages_health_check():
    """Health check for packages service."""
    return {
        "available": True,
        "service": "packages",
        "features": [
            "export_json",
            "export_yaml",
            "import_json",
            "import_yaml",
            "validation",
            "checksum_verification",
            "gzip_compression",
        ]
    }