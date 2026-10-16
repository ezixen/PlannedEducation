"""
Package/Module Routes for PlannedEducation
Endpoints for managing, sharing, and discovering test packages/modules.
Supports central repository, custom sources, categories, ratings, and versioning.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from . import database, models
from .routes_auth import get_current_user
from .schemas import (
    PackageCategoryEnum,
    PackageCreate,
    PackageExportRequest,
    PackageImportResult,
    PackageListFilters,
    PackageListResponse,
    PackageMetadataResponse,
    PackageRatingCreate,
    PackageRatingResponse,
    PackageResponse,
    PackageSourceCreate,
    PackageSourceResponse,
    PackageSourceUpdate,
    PackageStatusEnum,
    PackageUpdate,
    PackageValidationResult,
    PackageExportRequest,
    PackageImportResult,
    PackageValidationResult,
    PackageDownloadResponse,
    PackageRatingCreate,
    PackageRatingResponse,
    PackageSourceCreate,
    PackageSourceResponse,
    PackageSourceUpdate,
)

router = APIRouter(prefix="/packages", tags=["packages"])


# ── Helper Functions ────────────────────────────────────────────────────────

def _calculate_checksum(data: dict) -> str:
    """Calculate SHA-256 checksum of package content."""
    # Remove checksum field before calculating
    content = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(content.encode()).hexdigest()


def _validate_package_structure(pkg: dict) -> tuple[bool, list[str], list[str]]:
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
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
                "delivery_mode": "classroom",
                "allow_digital_hand_raise": False,
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
        filename = (
            f"{exam.title.replace(' ', '_')}_package.yaml.gz"
            if request.format == "yaml"
            else f"{exam.title.replace(' ', '_')}_package.json.gz"
        )
        return {
            "content": compressed,
            "media_type": "application/gzip",
            "filename": filename,
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
    if file.filename and file.filename.endswith(".gz"):
        import gzip

        try:
            content = gzip.decompress(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid gzip file") from e

    # Parse content
    try:
        if file.filename and file.filename.endswith((".yaml", ".yml")):
            pkg = yaml.safe_load(content.decode())
        else:
            pkg = json.loads(content.decode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid package format: {e}") from e

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
            id=str(uuid.uuid4()),
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
    for _r_data in pkg.get("rubrics", []):
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


# ── Package CRUD ────────────────────────────────────────────────────────────

@router.post("", response_model=PackageResponse, status_code=201)
async def create_package(
    package: PackageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a new package from an exam or package data."""
    # Verify the exam exists and user owns it
    exam_id = package.package_data.get("exam", {}).get("id")
    if exam_id:
        exam = db.query(models.Exam).filter(
            models.Exam.id == exam_id,
            models.Exam.teacher_id == current_user.id
        ).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found or access denied")
    
    # Calculate checksum
    pkg_data = package.package_data.copy()
    pkg_data["metadata"] = pkg_data.get("metadata", {}).copy()
    pkg_data["metadata"]["checksum"] = ""
    checksum = hashlib.sha256(json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    
    # Create package
    category_val = package.category.value if hasattr(package.category, "value") else package.category
    source_val = package.source_type.value if hasattr(package.source_type, "value") else str(package.source_type)
    tags_str = json.dumps(package.tags) if isinstance(package.tags, list) else (package.tags or "[]")
    data_str = json.dumps(package.package_data) if isinstance(package.package_data, dict) else str(package.package_data)

    pkg = models.Package(
        id=str(uuid.uuid4()),
        name=package.name,
        version=package.version,
        description=package.description,
        category=category_val,
        subject=package.subject,
        grade_level=package.grade_level,
        tags=tags_str,
        license=package.license,
        package_data=data_str,
        checksum=checksum,
        author_id=current_user.id,
        status=models.PackageStatus.published if package.is_public else models.PackageStatus.draft,
        is_public=package.is_public,
        source_type=source_val,
        source_url=package.source_url,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    
    return pkg


@router.get("", response_model=PackageListResponse)
async def list_packages(
    filters: PackageListFilters = Depends(),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List packages with filtering, pagination, and search."""
    query = db.query(models.Package)
    
    # Apply filters
    if filters.subject:
        query = query.filter(models.Package.subject.ilike(f"%{filters.subject}%"))
    if filters.grade_level:
        query = query.filter(models.Package.grade_level == filters.grade_level)
    if filters.category:
        query = query.filter(models.Package.category == filters.category)
    if filters.status:
        query = query.filter(models.Package.status == filters.status)
    if filters.is_public is not None:
        query = query.filter(models.Package.is_public == filters.is_public)
    if filters.author_id:
        query = query.filter(models.Package.author_id == filters.author_id)
    if filters.search:
        query = query.filter(
            or_(
                models.Package.name.ilike(f"%{filters.search}%"),
                models.Package.description.ilike(f"%{filters.search}%"),
                models.Package.tags.ilike(f"%{filters.search}%"),
            )
        )
    
    # Default: show public packages + user's own packages
    query = query.filter(
        or_(
            models.Package.is_public == True,
            models.Package.author_id == current_user.id
        )
    )
    
    # Order by relevance: public first, then by updated_at
    query = query.order_by(
        models.Package.is_public.desc(),
        models.Package.updated_at.desc()
    )
    
    total = query.count()
    packages = query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size).all()
    
    return PackageListResponse(
        packages=packages,
        total=total,
        page=filters.page,
        page_size=filters.page_size
    )


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
            "categories",
            "ratings",
            "forking",
            "custom_sources",
            "download_tracking",
        ]
    }


# ── Package Sources (Custom Repositories) ────────────────────────────────

@router.post("/sources", response_model=PackageSourceResponse, status_code=201)
async def create_package_source(
    source: PackageSourceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Add a custom package source (school admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can add package sources")
    
    source_type_val = source.source_type.value if hasattr(source.source_type, "value") else str(source.source_type)
    cats_str = json.dumps(source.allowed_categories) if isinstance(source.allowed_categories, list) else str(source.allowed_categories or "[]")
    tags_str = json.dumps(source.allowed_tags) if isinstance(source.allowed_tags, list) else str(source.allowed_tags or "[]")

    source_obj = models.PackageSource(
        id=str(uuid.uuid4()),
        name=source.name,
        url=source.url,
        api_key=source.api_key,
        source_type=source_type_val,
        is_enabled=source.is_enabled,
        is_default=source.is_default,
        priority=source.priority,
        auto_sync=source.auto_sync,
        sync_interval_hours=source.sync_interval_hours,
        allowed_categories=cats_str,
        allowed_tags=tags_str,
        school_id=getattr(current_user, "school_id", None),
    )
    db.add(source_obj)
    db.commit()
    db.refresh(source_obj)
    return source_obj


@router.get("/sources", response_model=list[PackageSourceResponse])
async def list_package_sources(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List configured package sources."""
    if current_user.is_admin:
        sources = db.query(models.PackageSource).all()
    else:
        # Regular users see only enabled default sources
        sources = db.query(models.PackageSource).filter(
            models.PackageSource.is_enabled == True,
            models.PackageSource.is_default == True
        ).all()
    return sources


@router.patch("/sources/{source_id}", response_model=PackageSourceResponse)
async def update_package_source(
    source_id: str,
    update: PackageSourceUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a package source (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update package sources")
    
    source = db.query(models.PackageSource).filter(models.PackageSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("allowed_categories", "allowed_tags") and isinstance(value, list):
            value = json.dumps(value)
        setattr(source, field, value)
    
    source.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=204)
async def delete_package_source(
    source_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a package source (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete package sources")
    
    source = db.query(models.PackageSource).filter(models.PackageSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()


# ── Package Sync (from external sources) ───────────────────────────────

@router.post("/sources/{source_id}/sync")
async def sync_package_source(
    source_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Manually trigger sync from a package source (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can trigger sync")
    
    source = db.query(models.PackageSource).filter(models.PackageSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    synced_count = 0
    try:
        import httpx
        headers = {}
        if source.api_key:
            headers["Authorization"] = f"Bearer {source.api_key}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(source.url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "packages" in data:
                    items = data["packages"]
                elif isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = [data]
                else:
                    items = []

                for item in items:
                    pkg_id = item.get("id") or str(uuid.uuid4())
                    raw_pkg_data = item.get("package_data", item)
                    pkg_data_str = json.dumps(raw_pkg_data) if isinstance(raw_pkg_data, dict) else str(raw_pkg_data)
                    tags_val = item.get("tags", [])
                    tags_str = json.dumps(tags_val) if isinstance(tags_val, list) else str(tags_val or "[]")
                    category_val = item.get("category", "other")
                    if hasattr(category_val, "value"):
                        category_val = category_val.value

                    existing = db.query(models.Package).filter(models.Package.id == pkg_id).first()
                    if not existing:
                        new_pkg = models.Package(
                            id=pkg_id,
                            name=item.get("name", "Synced Module"),
                            version=item.get("version", "1.0.0"),
                            description=item.get("description", ""),
                            category=category_val,
                            subject=item.get("subject", ""),
                            grade_level=item.get("grade_level", ""),
                            tags=tags_str,
                            license=item.get("license", "CC-BY-4.0"),
                            package_data=pkg_data_str,
                            checksum=item.get("checksum", "synced"),
                            author_id=current_user.id,
                            status=models.PackageStatus.published,
                            is_public=True,
                            source_type="custom",
                            source_url=source.url,
                        )
                        db.add(new_pkg)
                        synced_count += 1
                db.commit()
        source.last_synced_at = datetime.now(UTC)
        source.last_sync_status = "success"
        source.last_sync_error = None
        db.commit()
    except Exception as exc:
        source.last_synced_at = datetime.now(UTC)
        source.last_sync_status = "error"
        source.last_sync_error = str(exc)
        db.commit()
        return {"status": "sync_failed", "source_id": source_id, "error": str(exc)}
    
    return {"status": "success", "source_id": source_id, "synced_packages": synced_count}


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get a package by ID."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Check access: public packages or owner
    if not package.is_public and package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return package


@router.patch("/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: str,
    update: PackageUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a package (owner only)."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the author can update this package")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(package, field, value)
    
    package.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(package)
    
    return package


@router.delete("/{package_id}", status_code=204)
async def delete_package(
    package_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a package (owner only)."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the author can delete this package")
    
    db.delete(package)
    db.commit()


# ── Package Publishing & Discovery ────────────────────────────────────────

@router.post("/{package_id}/publish", response_model=PackageResponse)
async def publish_package(
    package_id: str,
    is_public: bool = Form(True),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Publish or unpublish a package to the central repository."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the author can publish this package")
    
    package.is_public = is_public
    package.status = models.PackageStatus.published if is_public else models.PackageStatus.draft
    if is_public and not package.published_at:
        package.published_at = datetime.now(UTC)
    package.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(package)
    
    return package


@router.post("/{package_id}/fork", response_model=PackageResponse)
async def fork_package(
    package_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Create a fork of an existing package."""
    original = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if not original.is_public and original.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot fork private package")
    
    # Create fork
    fork = models.Package(
        id=str(uuid.uuid4()),
        name=f"{original.name} (fork)",
        version="1.0.0",
        description=original.description,
        category=original.category,
        subject=original.subject,
        grade_level=original.grade_level,
        tags=original.tags,
        license=original.license,
        package_data=original.package_data,
        checksum=original.checksum,
        author_id=current_user.id,
        status=models.PackageStatus.draft,
        is_public=False,
        source_type=models.PackageSourceType.fork,
        parent_package_id=original.id,
    )
    db.add(fork)
    db.commit()
    db.refresh(fork)
    
    return fork


# ── Package Ratings ──────────────────────────────────────────────────────

@router.post("/{package_id}/rate", response_model=PackageRatingResponse)
async def rate_package(
    package_id: str,
    rating: PackageRatingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Rate a package (1-5 stars with optional review)."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if not package.is_public:
        raise HTTPException(status_code=403, detail="Cannot rate private package")
    
    # Check if user already rated
    existing = db.query(models.PackageRating).filter(
        models.PackageRating.package_id == package_id,
        models.PackageRating.user_id == current_user.id
    ).first()
    
    if existing:
        existing.rating = rating.rating
        existing.review = rating.review
        existing.updated_at = datetime.now(UTC)
    else:
        new_rating = models.PackageRating(
            id=str(uuid.uuid4()),
            package_id=package_id,
            user_id=current_user.id,
            rating=rating.rating,
            review=rating.review,
        )
        db.add(new_rating)
    
    # Update package rating stats
    ratings = db.query(models.PackageRating).filter(models.PackageRating.package_id == package_id).all()
    package.rating_avg = sum(r.rating for r in ratings) / len(ratings)
    package.rating_count = len(ratings)
    
    db.commit()
    
    # Return the rating
    rating_obj = db.query(models.PackageRating).filter(
        models.PackageRating.package_id == package_id,
        models.PackageRating.user_id == current_user.id
    ).first()
    return rating_obj


@router.get("/{package_id}/ratings", response_model=list[PackageRatingResponse])
async def get_package_ratings(
    package_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all ratings for a package."""
    ratings = db.query(models.PackageRating).filter(
        models.PackageRating.package_id == package_id
    ).order_by(desc(models.PackageRating.created_at)).all()
    return ratings


# ── Package Downloads ────────────────────────────────────────────────────

@router.get("/{package_id}/download", response_model=PackageDownloadResponse)
async def download_package(
    package_id: str,
    format: str = Query("json", pattern="^(json|yaml)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Download a package file."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if not package.is_public and package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Track download
    download = models.PackageDownload(
        id=str(uuid.uuid4()),
        package_id=package_id,
        user_id=current_user.id,
        source_type="direct",
    )
    db.add(download)
    package.download_count += 1
    db.commit()
    
    # Return package data
    pkg_data = json.loads(package.package_data)
    if format == "yaml":
        content = yaml.dump(pkg_data, default_flow_style=False, sort_keys=False)
        media_type = "application/yaml"
        filename = f"{package.name.replace(' ', '_')}_package.yaml"
    else:
        content = json.dumps(pkg_data, indent=2)
        media_type = "application/json"
        filename = f"{package.name.replace(' ', '_')}_package.json"
    
    return PackageDownloadResponse(
        content=content,
        media_type=media_type,
        filename=filename
    )




# ── Package Download Tracking ──────────────────────────────────────────

@router.post("/{package_id}/download", response_model=dict)
async def track_package_download(
    package_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Track a package download for statistics."""
    package = db.query(models.Package).filter(models.Package.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if not package.is_public and package.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    download = models.PackageDownload(
        id=str(uuid.uuid4()),
        package_id=package_id,
        user_id=current_user.id,
        source_type="direct",
    )
    db.add(download)
    package.download_count += 1
    db.commit()
    
    return {"status": "tracked", "download_count": package.download_count}
