from pathlib import Path
"""
test_all_countries_curriculum_modules.py
End-to-End test for ALL Countries Curriculum Test Modules
Tests that teachers can manually create, import, and use curriculum-aligned test modules
for Hungary, Germany, UK, USA, and Canada.
"""

import json
import os
import sys
import time

import httpx

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@testschool.edu")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "TestAdmin123!")

# Path to test modules
MODULES_BASE_PATH = os.getenv(
    "MODULES_BASE_PATH",
    str(Path(__file__).resolve().parents[1] / "plans" / "test-modules" / "modules")
)

# Country configurations
COUNTRIES = {
    "hungary": {
        "path": "hungary",
        "subject_map": {
            "english": "languages",
            "science": "other",
            "biology": "biology",
            "chemistry": "chemistry",
            "physics": "physics",
        },
        "expected_grades": ["grade-01", "grade-02", "grade-03", "grade-04", "grade-07", "grade-10"],
        "expected_subjects": {
            "grade-01": ["english", "science"],
            "grade-02": ["science"],
            "grade-03": ["science"],
            "grade-04": ["english", "science"],
            "grade-07": ["english", "science"],
            "grade-10": ["biology", "chemistry", "english", "physics"],
        }
    },
    "germany": {
        "path": "germany",
        "subject_map": {
            "englisch": "languages",
            "science": "other",
            "physik": "physics",
            "chemie": "chemistry",
        },
        "expected_grades": ["grade-01", "grade-04", "grade-07", "grade-10"],
        "expected_subjects": {
            "grade-01": ["englisch"],
            "grade-04": ["science"],
            "grade-07": ["englisch", "science"],
            "grade-10": ["physik", "chemie"],
        }
    },
    "uk": {
        "path": "uk",
        "subject_map": {
            "english": "languages",
            "science": "other",
            "physics": "physics",
            "chemistry": "chemistry",
        },
        "expected_grades": ["grade-01", "grade-04", "grade-07", "grade-10"],
        "expected_subjects": {
            "grade-01": ["english"],
            "grade-04": ["science"],
            "grade-07": ["english", "science"],
            "grade-10": ["physics", "chemistry"],
        }
    },
    "usa": {
        "path": "usa",
        "subject_map": {
            "english": "languages",
            "science": "other",
            "physics": "physics",
            "chemistry": "chemistry",
        },
        "expected_grades": ["grade-01", "grade-04", "grade-07", "grade-10"],
        "expected_subjects": {
            "grade-01": ["english"],
            "grade-04": ["english", "science"],
            "grade-07": ["english", "science"],
            "grade-10": ["physics"],
        }
    },
    "canada": {
        "path": "canada",
        "subject_map": {
            "english": "languages",
            "science": "other",
            "physics": "physics",
            "chemistry": "chemistry",
        },
        "expected_grades": ["grade-01", "grade-04", "grade-07", "grade-10"],
        "expected_subjects": {
            "grade-01": ["english"],
            "grade-04": ["english", "science"],
            "grade-07": ["science"],
            "grade-10": ["physics", "chemistry"],
        }
    },
}


def print_step(title: str):
    print(f"\n{'='*70}\n>> {title}\n{'='*70}")


def load_module(module_path: str) -> dict:
    """Load a test module from JSON file."""
    with open(module_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_country_modules(country_path: str) -> list:
    """Get all test module files for a country."""
    modules = []
    full_path = os.path.join(MODULES_BASE_PATH, country_path)
    for root, dirs, files in os.walk(full_path):
        for file in files:
            if file.endswith(".json"):
                module_full_path = os.path.join(root, file)
                rel_path = os.path.relpath(module_full_path, full_path)
                modules.append((rel_path, module_full_path))
    return sorted(modules)


def run_country_modules(client, admin_headers, teacher_headers, country_name, country_config):
    """Test all modules for a specific country."""
    print_step(f"Testing {country_name.upper()} Curriculum Modules")
    
    modules = get_country_modules(country_config["path"])
    print(f"Found {len(modules)} {country_name} test modules:")
    for rel_path, _ in modules:
        print(f"  - {rel_path}")
    
    assert len(modules) > 0, f"No {country_name} modules found!"
    
    created_exam_ids = []
    grade_subjects = {}
    
    for rel_path, full_path in modules:
        print(f"\n  Testing module: {rel_path}")
        module = load_module(full_path)
        
        # Validate module structure
        assert "metadata" in module, "Module missing metadata"
        assert "exam" in module, "Module missing exam"
        assert "questions" in module, "Module missing questions"
        assert len(module["questions"]) > 0, "Module has no questions"
        
        metadata = module["metadata"]
        exam_data = module["exam"]
        questions = module["questions"]
        
        print(f"    Subject: {metadata.get('subject', 'N/A')}")
        print(f"    Grade: {metadata.get('grade_level', 'N/A')}")
        print(f"    Questions: {len(questions)}")
        print(f"    Duration: {exam_data.get('duration_minutes', 'N/A')} minutes")
        print(f"    Total Points: {metadata.get('total_points', 'N/A')}")
        
        # Track grade/subject coverage
        grade = metadata.get("grade_level", "")
        subject = metadata.get("subject", "")
        if grade not in grade_subjects:
            grade_subjects[grade] = set()
        grade_subjects[grade].add(subject)
        
        # Create exam from module
        create_exam_resp = client.post(
            "/exams/",
            headers=teacher_headers,
            json={
                "title": exam_data["title"],
                "description": exam_data.get("description", ""),
                "duration_minutes": exam_data.get("duration_minutes", 45),
                "seb_config_key": None,
            },
        )
        assert create_exam_resp.status_code == 201, f"Exam creation failed: {create_exam_resp.text}"
        exam = create_exam_resp.json()
        exam_id = exam["id"]
        created_exam_ids.append(exam_id)
        print(f"    Exam created: {exam_id}")

        # Add questions from module
        for q_data in questions:
            q_resp = client.post(
                f"/exams/{exam_id}/questions",
                headers=teacher_headers,
                json={
                    "question_type": q_data["question_type"],
                    "text": q_data["text"],
                    "options_json": json.dumps(q_data["options"]) if q_data.get("options") else None,
                    "correct_answer": q_data.get("correct_answer"),
                    "rubric": q_data.get("rubric"),
                    "points": q_data.get("points", 1),
                },
            )
            assert q_resp.status_code == 201, f"Question creation failed: {q_resp.text}"
        
        print(f"    Added {len(questions)} questions to exam")

        # Verify exam has all questions
        my_exams = client.get("/exams/mine", headers=teacher_headers)
        assert my_exams.status_code == 200
        my_exam = next((e for e in my_exams.json() if e["id"] == exam_id), None)
        assert my_exam, "Exam not found in teacher's exams"
        assert len(my_exam["questions"]) == len(questions), \
            f"Question count mismatch: expected {len(questions)}, got {len(my_exam['questions'])}"
        print(f"    Verified: {len(my_exam['questions'])} questions in exam")

    print(f"\n  Successfully created {len(created_exam_ids)} exams from {country_name} modules")
    
    # Verify grade/subject coverage
    print(f"\n  {country_name.upper()} Curriculum Coverage:")
    for grade in sorted(grade_subjects.keys()):
        subjects = sorted(grade_subjects[grade])
        print(f"    {grade}: {', '.join(subjects)}")
    
    # Verify expected grades
    for grade in country_config["expected_grades"]:
        assert grade in grade_subjects, f"Missing grade: {grade}"
    
    # Verify expected subjects per grade
    for grade, expected_subjects in country_config["expected_subjects"].items():
        for subject in expected_subjects:
            assert subject in grade_subjects.get(grade, set()), \
                f"Missing subject {subject} for {grade}"
    
    print(f"\n  All expected {country_name} grades and subjects verified!")
    
    return created_exam_ids, grade_subjects, modules


def run_package_workflow(client, teacher_headers, first_exam_id, first_module, country_name, subject_map):
    """Test package export/import/publish/download workflow."""
    print_step(f"Package Workflow for {country_name.upper()}")
    
    # Export first exam as package
    export_resp = client.post(
        "/packages/export",
        headers=teacher_headers,
        json={
            "exam_id": first_exam_id,
            "include_answers": True,
            "include_rubrics": True,
            "include_variables": True,
            "format": "json",
            "compress": False,
        },
    )
    assert export_resp.status_code == 200, f"Export failed: {export_resp.text}"
    export_data = export_resp.json()
    package_json_str = export_data["content"]
    package_dict = json.loads(package_json_str)
    filename = export_data["filename"]
    print(f"Exam exported as package: '{filename}'")
    print(f"  - Package Name: {package_dict['metadata']['name']}")
    print(f"  - Checksum: {package_dict['metadata']['checksum']}")
    print(f"  - Questions bundled: {len(package_dict['questions'])}")

    # Validate package
    files = {"file": (filename, package_json_str.encode("utf-8"), "application/json")}
    val_resp = client.post("/packages/validate", headers=teacher_headers, files=files)
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True, f"Validation failed: {val_data}"
    print("Package validation passed.")

    # Import package to create replicated exam
    files = {"file": (filename, package_json_str.encode("utf-8"), "application/json")}
    import_resp = client.post("/packages/import", headers=teacher_headers, files=files)
    assert import_resp.status_code == 200, f"Import failed: {import_resp.text}"
    import_data = import_resp.json()
    assert import_data["success"] is True
    new_exam_id = import_data["exam_id"]
    print(f"Package imported into new exam: {new_exam_id}")
    print(f"  - Questions imported: {import_data['questions_imported']}")

    # Publish module to catalog
    first_subject = first_module['metadata']['subject']
    publish_req = {
        "name": f"{country_name.upper()} - {first_module['metadata']['name']}",
        "version": first_module['metadata']['version'],
        "description": first_module['metadata']['description'],
        "category": subject_map.get(first_subject, "other"),
        "subject": first_subject.capitalize(),
        "grade_level": first_module['metadata']['grade_level'].replace('grade-', 'Grade '),
        "tags": first_module['metadata']['tags'],
        "license": first_module['metadata']['license'],
        "is_public": True,
        "package_data": first_module,
    }
    create_pkg_resp = client.post("/packages", headers=teacher_headers, json=publish_req)
    assert create_pkg_resp.status_code == 201, f"Create package failed: {create_pkg_resp.text}"
    created_pkg = create_pkg_resp.json()
    published_pkg_id = created_pkg["id"]
    print(f"{country_name} module published to catalog! Package ID: {published_pkg_id}")
    print(f"  - Name: {created_pkg['name']}")
    print(f"  - Category: {created_pkg['category']}")
    print(f"  - Subject: {created_pkg['subject']}")
    print(f"  - Grade: {created_pkg['grade_level']}")
    print(f"  - Tags: {created_pkg['tags']}")

    # Browse published packages - use the mapped category
    browse_category = subject_map.get(first_subject, "other")
    browse_resp = client.get(
        f"/packages?category={browse_category}&is_public=true",
        headers=teacher_headers
    )
    assert browse_resp.status_code == 200
    browse_data = browse_resp.json()
    found = [p for p in browse_data["packages"] if p["id"] == published_pkg_id]
    assert len(found) > 0, "Published package not found in catalog search!"
    print(f"Catalog search verified: Package '{found[0]['name']}' is discoverable.")

    # Download package
    dl_resp = client.get(f"/packages/{published_pkg_id}/download", headers=teacher_headers)
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()
    assert "content" in dl_data
    print(f"Package download verified: Received file '{dl_data['filename']}' ({len(dl_data['content'])} bytes).")
    
    return published_pkg_id


def run_student_workflow(client, teacher_headers, first_exam_id, country_name):
    """Test student taking exam and teacher reviewing."""
    print_step(f"Student Workflow for {country_name.upper()}")
    
    unique_suffix = int(time.time())
    student_email = f"{country_name}_student_{unique_suffix}@peschool.edu"
    student_user = f"{country_name}_student_{unique_suffix}"
    student_pass = "StudentPass123!"

    reg_student = client.post(
        "/auth/register",
        json={
            "email": student_email,
            "username": student_user,
            "full_name": f"Test Student {country_name}",
            "password": student_pass,
            "role": "student",
        },
    )
    assert reg_student.status_code == 201, f"Student reg failed: {reg_student.text}"
    print(f"Student registered: {student_email}")

    student_login = client.post(
        "/auth/token",
        data={"username": student_email, "password": student_pass},
    )
    assert student_login.status_code == 200
    student_token = student_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("Student authenticated successfully.")

    # Student starts exam session
    seb_headers = {
        **student_headers,
        "X-SafeExamBrowser-RequestHash": "dev-bypass",
    }
    start_resp = client.post(f"/exams/{first_exam_id}/start", headers=seb_headers)
    assert start_resp.status_code == 200, f"Start exam failed: {start_resp.text}"
    start_data = start_resp.json()
    submission_id = start_data["submission_id"]
    served_questions = start_data["questions"]
    print(f"Exam session started! Submission ID: {submission_id}")
    print(f"Received {len(served_questions)} questions.")

    # Verify answers and rubrics are absent from student's exam packet
    for sq in served_questions:
        assert "correct_answer" not in sq, "Security alert: correct answer exposed to student!"
        assert "rubric" not in sq, "Security alert: rubric exposed to student!"
    print("Security check passed: Student questions packet clean of answer keys.")

    # Student submits answers
    student_answers = []
    for sq in served_questions:
        q_type = sq["question_type"]
        if q_type == "multiple_choice":
            ans_val = sq.get("options", ["A"])[0] if sq.get("options") else "A"
        elif q_type == "dynamic_math":
            ans_val = "42"
        else:
            ans_val = f"Sample essay response for {country_name} curriculum test."
        student_answers.append({"question_id": sq["question_id"], "response": ans_val})

    submit_resp = client.post(
        f"/exams/{first_exam_id}/submit",
        headers=seb_headers,
        json={"answers": student_answers},
    )
    assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
    print(f"Exam submission result: {submit_resp.json()}")

    # Teacher reviews submission
    heartbeats_resp = client.get(f"/exams/{first_exam_id}/heartbeats", headers=teacher_headers)
    assert heartbeats_resp.status_code == 200
    hb_data = heartbeats_resp.json()
    student_sub_entry = next(
        (h for h in hb_data["heartbeats"] if h["submission_id"] == submission_id), 
        None
    )
    assert student_sub_entry, "Student submission not found in heartbeats"
    print(f"Teacher dashboard saw submission: {student_sub_entry['student_name']} (is_complete: {student_sub_entry['is_complete']})")
    assert student_sub_entry["is_complete"] is True


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 1: Server Health Check
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 1: Verify Server Health & Module Engine")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    health_data = resp.json()
    print(f"Server health status: {health_data}")
    assert health_data.get("status") == "ok"

    pkg_health = client.get("/packages/health")
    assert pkg_health.status_code == 200, f"Package health failed: {pkg_health.text}"
    print(f"Package engine health: {pkg_health.json()}")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 2: Administrator Authentication
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 2: Administrator Authentication")
    admin_login = client.post(
        "/auth/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_tokens = admin_login.json()
    admin_token = admin_tokens["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin login successful. Token acquired.")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 3: Teacher Registration & Approval
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 3: Teacher Registration & Approval")
    unique_suffix = int(time.time())
    teacher_email = f"all_countries_teacher_{unique_suffix}@peschool.edu"
    teacher_user = f"all_countries_teacher_{unique_suffix}"
    teacher_pass = "TeacherPass123!"

    reg_teacher = client.post(
        "/auth/register",
        json={
            "email": teacher_email,
            "username": teacher_user,
            "full_name": "Dr. International Teacher",
            "password": teacher_pass,
            "role": "teacher",
        },
    )
    assert reg_teacher.status_code == 201, f"Teacher reg failed: {reg_teacher.text}"
    print(f"Teacher registered: {teacher_email}")

    teacher_login = client.post(
        "/auth/token",
        data={"username": teacher_email, "password": teacher_pass},
    )
    assert teacher_login.status_code == 200
    teacher_token = teacher_login.json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    print("Teacher authenticated successfully.")

    # Check if teacher needs approval (in test mode, teachers without "pending" in name are auto-approved)
    pending = client.get("/admin/pending-teachers", headers=admin_headers)
    assert pending.status_code == 200
    pending_teachers = pending.json()
    our_teacher = next((t for t in pending_teachers if t["email"] == teacher_email), None)
    
    if our_teacher:
        # Teacher needs approval
        approve = client.post(
            f"/admin/teachers/{our_teacher['id']}/approve",
            headers=admin_headers,
        )
        assert approve.status_code == 200
        print(f"Teacher approved: {approve.json()['message']}")
        
        # Teacher logs in again after approval
        teacher_login = client.post(
            "/auth/token",
            data={"username": teacher_email, "password": teacher_pass},
        )
        assert teacher_login.status_code == 200
        teacher_token = teacher_login.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        print("Teacher re-authenticated after approval.")
    else:
        # Teacher was auto-approved (test mode behavior)
        print("Teacher was auto-approved (test mode).")
        # Re-login to get fresh token with approved status
        teacher_login = client.post(
            "/auth/token",
            data={"username": teacher_email, "password": teacher_pass},
        )
        assert teacher_login.status_code == 200
        teacher_token = teacher_login.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        print("Teacher re-authenticated.")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 4: Test All Countries
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 4: Test All Countries Curriculum Modules")
    
    all_results = {}
    total_modules = 0
    total_exams = 0
    
    for country_name, country_config in COUNTRIES.items():
        try:
            created_exam_ids, grade_subjects, modules = run_country_modules(
                client, admin_headers, teacher_headers, country_name, country_config
            )
            all_results[country_name] = {
                "exam_ids": created_exam_ids,
                "grade_subjects": grade_subjects,
                "modules": modules,
            }
            total_modules += len(modules)
            total_exams += len(created_exam_ids)
        except Exception as e:
            print(f"ERROR testing {country_name}: {e}")
            raise

    print(f"\n  Total modules tested: {total_modules}")
    print(f"  Total exams created: {total_exams}")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 5: Package Workflow for Each Country
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 5: Package Workflow for Each Country")
    
    for country_name, country_config in COUNTRIES.items():
        result = all_results[country_name]
        first_exam_id = result["exam_ids"][0]
        first_module_path = result["modules"][0][1]
        first_module = load_module(first_module_path)
        
        run_package_workflow(
            client, teacher_headers, first_exam_id, first_module, 
            country_name, country_config["subject_map"]
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 6: Student Workflow for Each Country
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 6: Student Workflow for Each Country")
    
    for country_name, country_config in COUNTRIES.items():
        result = all_results[country_name]
        first_exam_id = result["exam_ids"][0]
        
        run_student_workflow(client, teacher_headers, first_exam_id, country_name)

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 7: Summary
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("ALL COUNTRIES CURRICULUM MODULE TESTS PASSED!")
    print(f"Countries tested: {', '.join(COUNTRIES.keys())}")
    print(f"Total modules: {total_modules}")
    print(f"Total exams created: {total_exams}")
    print(f"Total packages published: {len(COUNTRIES)}")
    print("Teacher manual creation workflow verified end-to-end for all countries.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as ae:
        print(f"\n[FAIL] Assertion failed: {ae}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)