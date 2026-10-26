"""
test_germany_curriculum_modules.py
Verification suite for Germany Bildungspläne curriculum test modules.
Ensures teachers have comprehensive, structured, curriculum-aligned modules across grades 1-12.
"""

import json
import os
from pathlib import Path
import pytest

GERMANY_MODULES_PATH = Path(__file__).resolve().parents[1] / "plans" / "test-modules" / "modules" / "germany"


def get_all_germany_modules():
    modules = []
    for root, _, files in os.walk(GERMANY_MODULES_PATH):
        for file in files:
            if file.endswith(".json"):
                full_path = Path(root) / file
                rel_path = full_path.relative_to(GERMANY_MODULES_PATH)
                modules.append((rel_path, full_path))
    return sorted(modules)


def test_germany_curriculum_directory_structure():
    """Verify that Germany curriculum covers all 12 grades and core subjects."""
    assert GERMANY_MODULES_PATH.exists(), f"Germany modules path {GERMANY_MODULES_PATH} does not exist"
    
    modules = get_all_germany_modules()
    assert len(modules) > 0, "No Germany curriculum modules found!"

    # Map grades and subjects
    grades_found = set()
    subjects_by_grade = {}

    for rel_path, _ in modules:
        parts = rel_path.parts
        assert len(parts) >= 2, f"Module path {rel_path} does not follow grade/subject structure"
        grade = parts[0]
        subject = parts[1]
        grades_found.add(grade)
        subjects_by_grade.setdefault(grade, set()).add(subject)

    # Check that grades 1 through 12 are all present
    expected_grades = [f"grade-{i:02d}" for i in range(1, 13)]
    for grade in expected_grades:
        assert grade in grades_found, f"Missing grade level in Germany curriculum: {grade}"

    # Verify key subject offerings across primary and secondary tiers
    assert "math" in subjects_by_grade["grade-01"]
    assert "science" in subjects_by_grade["grade-01"]
    assert "math" in subjects_by_grade["grade-07"]
    assert "math" in subjects_by_grade["grade-12"]
    assert "biology" in subjects_by_grade["grade-12"]
    assert "history" in subjects_by_grade["grade-12"]


def test_germany_module_schema_and_curriculum_alignment():
    """Verify that every Germany module adheres to the standard schema and Bildungspläne curriculum."""
    modules = get_all_germany_modules()
    assert len(modules) >= 10, f"Expected at least 10 Germany modules, found {len(modules)}"

    for rel_path, full_path in modules:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data, f"{rel_path}: Missing metadata key"
        assert "exam" in data, f"{rel_path}: Missing exam key"
        assert "questions" in data, f"{rel_path}: Missing questions key"

        meta = data["metadata"]
        assert meta.get("curriculum") in ["germany-bildungsplaene", "deutschland-bildungsplaene"], (
            f"{rel_path}: curriculum must be 'germany-bildungsplaene' or 'deutschland-bildungsplaene', got '{meta.get('curriculum')}'"
        )
        assert meta.get("country") in ["germany", "de", "Deutschland"], (
            f"{rel_path}: country must indicate Germany"
        )

        exam = data["exam"]
        assert "title" in exam and len(exam["title"].strip()) > 0, f"{rel_path}: Missing exam title"
        assert exam.get("duration_minutes", 0) > 0, f"{rel_path}: Invalid duration_minutes"

        questions = data["questions"]
        assert len(questions) > 0, f"{rel_path}: Module has no questions"

        total_pts = 0
        for q_idx, q in enumerate(questions):
            assert "question_type" in q, f"{rel_path} Q{q_idx}: Missing question_type"
            assert q["question_type"] in ["multiple_choice", "essay", "dynamic_math"], (
                f"{rel_path} Q{q_idx}: Invalid question_type '{q['question_type']}'"
            )
            assert "text" in q and len(q["text"].strip()) > 0, f"{rel_path} Q{q_idx}: Empty question text"
            pts = q.get("points", 1)
            assert pts > 0, f"{rel_path} Q{q_idx}: Points must be > 0"
            total_pts += pts

            if q["question_type"] == "multiple_choice":
                has_options = ("options" in q and isinstance(q["options"], list) and len(q["options"]) >= 2)
                has_options_json = ("options_json" in q and bool(q["options_json"]))
                assert has_options or has_options_json, (
                    f"{rel_path} Q{q_idx}: Multiple choice question must have options or options_json"
                )

        assert total_pts >= 1, f"{rel_path}: Total points must be at least 1"


def test_germany_curriculum_documentation_exists():
    """Verify that official reference docs for German Bildungspläne exist in curriculum_docs/germany."""
    curriculum_docs_path = Path(__file__).resolve().parents[1] / "curriculum_docs" / "germany"
    assert curriculum_docs_path.exists(), f"{curriculum_docs_path} does not exist"
    
    docs = list(curriculum_docs_path.glob("*.pdf")) + list(curriculum_docs_path.glob("*.md"))
    assert len(docs) > 0, "No curriculum documentation found in curriculum_docs/germany"
