"""
test_mit_curriculum_modules.py
Verification suite for MIT OpenCourseWare university-level curriculum modules and reference docs.
Ensures higher education assessment packages conform to rigorous academic standards.
"""

import json
import os
from pathlib import Path
import pytest

MIT_DOCS_PATH = Path(__file__).resolve().parents[1] / "curriculum_docs" / "university" / "mit"
MIT_MODULES_PATH = Path(__file__).resolve().parents[1] / "plans" / "test-modules" / "modules" / "university" / "mit"


def test_mit_curriculum_reference_documents():
    """Verify that official MIT OCW curriculum reference documents exist and are populated."""
    assert MIT_DOCS_PATH.exists(), f"MIT docs directory {MIT_DOCS_PATH} does not exist"

    expected_files = [
        "README.md",
        "mit_6_0001_python_programming.md",
        "mit_18_06_linear_algebra.md",
        "mit_8_01_classical_mechanics.md",
        "mit_18_01_single_variable_calculus.md",
    ]

    for fname in expected_files:
        doc_path = MIT_DOCS_PATH / fname
        assert doc_path.exists(), f"Missing MIT curriculum reference: {fname}"
        content = doc_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 200, f"MIT curriculum file {fname} is incomplete or empty"

    # Verify open access and license statement
    readme = (MIT_DOCS_PATH / "README.md").read_text(encoding="utf-8")
    assert "OpenCourseWare" in readme
    assert "CC BY-NC-SA" in readme or "Creative Commons" in readme
    assert "openly accessible without registration" in readme.lower() or "open access" in readme.lower()


def test_mit_test_modules_structure_and_coverage():
    """Verify that all generated MIT assessment modules exist and cover key higher ed subjects."""
    assert MIT_MODULES_PATH.exists(), f"MIT modules directory {MIT_MODULES_PATH} does not exist"

    expected_courses = ["cs-6-0001", "math-18-06", "physics-8-01"]
    for course in expected_courses:
        course_dir = MIT_MODULES_PATH / course
        assert course_dir.exists(), f"Missing course directory: {course}"
        json_files = list(course_dir.glob("*.json"))
        assert len(json_files) >= 1, f"No assessment modules found in {course_dir}"


def test_mit_modules_schema_and_academic_rigor():
    """Verify that MIT modules conform to the exam module schema with rubrics and point totals."""
    modules = list(MIT_MODULES_PATH.rglob("*.json"))
    assert len(modules) >= 5, f"Expected at least 5 MIT modules, found {len(modules)}"

    for mod_path in modules:
        with open(mod_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data, f"{mod_path.name}: Missing metadata"
        assert "exam" in data, f"{mod_path.name}: Missing exam"
        assert "questions" in data, f"{mod_path.name}: Missing questions"

        meta = data["metadata"]
        assert meta.get("curriculum", "").startswith("mit-ocw"), f"{mod_path.name}: Curriculum must start with 'mit-ocw'"
        assert "MIT" in meta.get("institution", "")
        assert meta.get("grade_level") in ["undergraduate", "university", "college"] or "college" in meta.get("tags", [])

        exam = data["exam"]
        assert len(exam.get("title", "").strip()) > 0
        assert exam.get("duration_minutes", 0) >= 30

        questions = data["questions"]
        assert len(questions) >= 2, f"{mod_path.name}: University exams should have at least 2 questions"

        total_pts = 0
        for q_idx, q in enumerate(questions):
            assert "question_type" in q, f"{mod_path.name} Q{q_idx}: Missing question_type"
            assert q["question_type"] in ["multiple_choice", "essay", "dynamic_math", "open_response", "code"]
            assert len(q.get("text", "").strip()) > 0, f"{mod_path.name} Q{q_idx}: Empty question text"
            pts = q.get("points", 1)
            assert pts > 0
            total_pts += pts

            if q["question_type"] == "multiple_choice":
                assert "options" in q or "options_json" in q
            elif q["question_type"] in ["essay", "open_response"]:
                assert "rubric" in q, f"{mod_path.name} Q{q_idx}: University essay/open_response questions require a grading rubric"

        assert total_pts >= 10, f"{mod_path.name}: Expected at least 10 total points"
