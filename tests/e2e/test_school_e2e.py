"""
test_school_e2e.py
Complete End-to-End Deployment & Integration Test for PlannedEducation
Tests the native school server deployment on http://127.0.0.1:8000:
1. Health & system readiness
2. Administrator authentication
3. Teacher registration, exam creation, and question authoring
4. Student registration, exam taking, answering, and submission
5. Teacher review & submission tracking
6. Module/Package export, validation, import, publishing, and download
7. Custom school module repository source registration, browsing, and synchronization
"""

import json
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"


def print_step(title: str):
    print(f"\n{'='*70}\n>> {title}\n{'='*70}")


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

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
        data={"username": "admin@peschool.edu", "password": "AdminPassword123!"},
    )
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_tokens = admin_login.json()
    admin_token = admin_tokens["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin login successful. Token acquired.")

    admin_me = client.get("/auth/me", headers=admin_headers)
    assert admin_me.status_code == 200
    print(f"Admin details verified: {admin_me.json()['email']} (role: {admin_me.json().get('role')})")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 3: Teacher Flow - Register, Login, Create Exam & Questions
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 3: Teacher Flow - Register, Login, Create Exam & Questions")
    unique_suffix = int(time.time())
    teacher_email = f"teacher_{unique_suffix}@peschool.edu"
    teacher_user = f"teacher_{unique_suffix}"
    teacher_pass = "TeacherPass123!"

    reg_teacher = client.post(
        "/auth/register",
        json={
            "email": teacher_email,
            "username": teacher_user,
            "full_name": "Dr. Franklin Miller",
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

    # Create Exam
    seb_secret = "seb_exam_secret_key_2026"
    create_exam_resp = client.post(
        "/exams/",
        headers=teacher_headers,
        json={
            "title": "Physics 101: Energy & Mechanics",
            "description": "Comprehensive midterm covering Newtonian mechanics and energy conservation laws.",
            "duration_minutes": 60,
            "seb_config_key": seb_secret,
        },
    )
    assert create_exam_resp.status_code == 201, f"Exam creation failed: {create_exam_resp.text}"
    exam = create_exam_resp.json()
    exam_id = exam["id"]
    print(f"Exam created successfully: '{exam['title']}' (ID: {exam_id})")

    # Add Question 1: Multiple Choice
    q1_resp = client.post(
        f"/exams/{exam_id}/questions",
        headers=teacher_headers,
        json={
            "question_type": "multiple_choice",
            "text": "What is the SI unit of Force?",
            "options_json": json.dumps(["Newton", "Joule", "Pascal", "Watt"]),
            "correct_answer": "Newton",
            "points": 5,
        },
    )
    assert q1_resp.status_code == 201, f"Q1 failed: {q1_resp.text}"
    q1_id = q1_resp.json()["id"]
    print(f"Question 1 (Multiple Choice) created: ID={q1_id}")

    # Add Question 2: Dynamic Math
    q2_resp = client.post(
        f"/exams/{exam_id}/questions",
        headers=teacher_headers,
        json={
            "question_type": "dynamic_math",
            "text": "A mass of 10kg undergoes an acceleration of [rand:2-5] m/s^2. What is the applied force?",
            "correct_answer": "F = m * a",
            "points": 5,
        },
    )
    assert q2_resp.status_code == 201, f"Q2 failed: {q2_resp.text}"
    q2_id = q2_resp.json()["id"]
    print(f"Question 2 (Dynamic Math) created: ID={q2_id}")

    # Add Question 3: Essay
    q3_resp = client.post(
        f"/exams/{exam_id}/questions",
        headers=teacher_headers,
        json={
            "question_type": "essay",
            "text": "State the Law of Conservation of Energy and explain how it applies to a swinging pendulum.",
            "rubric": "Full credit for stating energy cannot be created or destroyed, only transformed, and explaining the interchange between potential and kinetic energy.",
            "points": 10,
        },
    )
    assert q3_resp.status_code == 201, f"Q3 failed: {q3_resp.text}"
    q3_id = q3_resp.json()["id"]
    print(f"Question 3 (Essay) created: ID={q3_id}")

    # Verify teacher can see full exam details with answers
    my_exams = client.get("/exams/mine", headers=teacher_headers)
    assert my_exams.status_code == 200
    my_exam = [e for e in my_exams.json() if e["id"] == exam_id][0]
    print(f"Teacher verified exam in /exams/mine: {len(my_exam['questions'])} questions configured.")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 4: Student Flow - Register, Browse, Take & Submit Exam
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 4: Student Flow - Register, Browse, Take & Submit Exam")
    student_email = f"student_{unique_suffix}@peschool.edu"
    student_user = f"student_{unique_suffix}"
    student_pass = "StudentPass123!"

    reg_student = client.post(
        "/auth/register",
        json={
            "email": student_email,
            "username": student_user,
            "full_name": "Bob Robinson",
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

    # Student lists available exams - check that questions and answers are NOT leaked
    public_exams = client.get("/exams/", headers=student_headers)
    assert public_exams.status_code == 200
    for e in public_exams.json():
        assert "questions" not in e, "Security alert: questions leaked in public exam listing!"
        assert "correct_answer" not in str(e), "Security alert: answers leaked in public exam listing!"
    print("Security check passed: Public exam listing contains metadata only (zero leak).")

    # Student starts exam session
    # SEB verification: pass 'dev-bypass' header
    seb_headers = {
        **student_headers,
        "X-SafeExamBrowser-RequestHash": "dev-bypass",
    }
    start_resp = client.post(f"/exams/{exam_id}/start", headers=seb_headers)
    assert start_resp.status_code == 200, f"Start exam failed: {start_resp.text}"
    start_data = start_resp.json()
    submission_id = start_data["submission_id"]
    served_questions = start_data["questions"]
    print(f"Exam session started! Submission ID: {submission_id}")
    print(f"Received {len(served_questions)} questions tailored for student.")

    # Verify answers and rubrics are absent from student's exam packet
    for sq in served_questions:
        assert "correct_answer" not in sq, "Security alert: correct answer exposed to student!"
        assert "rubric" not in sq, "Security alert: rubric exposed to student!"
        print(f"  - [{sq['question_type']}] {sq['text']} ({sq['points']} pts)")
    print("Security check passed: Student questions packet completely clean of answer keys.")

    # Student submits heartbeat
    hb_resp = client.post(
        f"/exams/{exam_id}/heartbeat",
        headers=student_headers,
        json={"timestamp": int(time.time() * 1000), "status": "active"},
    )
    assert hb_resp.status_code == 200
    print("Student heartbeat successfully recorded.")

    # Prepare answers
    student_answers = []
    for sq in served_questions:
        q_type = sq["question_type"]
        if q_type == "multiple_choice":
            ans_val = "Newton"
        elif q_type == "dynamic_math":
            ans_val = "40"
        else:
            ans_val = (
                "The Law of Conservation of Energy states that energy can neither be created nor destroyed, "
                "only transformed from one form to another. In a swinging pendulum, potential energy at the highest "
                "point is converted into kinetic energy at the bottom of the swing, and back again."
            )
        student_answers.append({"question_id": sq["question_id"], "response": ans_val})

    # Student submits exam
    submit_resp = client.post(
        f"/exams/{exam_id}/submit",
        headers=seb_headers,
        json={"answers": student_answers},
    )
    assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
    print(f"Exam submission result: {submit_resp.json()}")

    # Idempotency check: duplicate submit must be rejected with 409
    dup_submit = client.post(
        f"/exams/{exam_id}/submit",
        headers=seb_headers,
        json={"answers": student_answers},
    )
    assert dup_submit.status_code == 409, f"Expected 409 on duplicate submit, got {dup_submit.status_code}"
    print("Idempotency verified: Re-submission correctly rejected with 409 Conflict.")

    # Student checks submission status
    my_sub_resp = client.get(f"/exams/{exam_id}/my-submission", headers=student_headers)
    assert my_sub_resp.status_code == 200
    print(f"Student confirmed submission status: completed_at={my_sub_resp.json()['completed_at']}")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 5: Teacher Monitoring & Review
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 5: Teacher Monitoring & Submission Tracking")
    heartbeats_resp = client.get(f"/exams/{exam_id}/heartbeats", headers=teacher_headers)
    assert heartbeats_resp.status_code == 200
    hb_data = heartbeats_resp.json()
    student_sub_entry = [h for h in hb_data["heartbeats"] if h["submission_id"] == submission_id][0]
    print(f"Teacher dashboard saw submission: {student_sub_entry['student_name']} (is_complete: {student_sub_entry['is_complete']})")
    assert student_sub_entry["is_complete"] is True

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 6: Module / Package System (Export, Validate, Import, Publish, Download)
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 6: Module System - Export, Validate, Import, Publish & Download")

    # 1. Export exam to .pepkg.json
    export_resp = client.post(
        "/packages/export",
        headers=teacher_headers,
        json={
            "exam_id": exam_id,
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
    print(f"Exam successfully exported as package: '{filename}'")
    print(f"  - Package Name: {package_dict['metadata']['name']}")
    print(f"  - Checksum: {package_dict['metadata']['checksum']}")
    print(f"  - Questions bundled: {len(package_dict['questions'])}")

    # 2. Validate package file
    files = {"file": (filename, package_json_str.encode("utf-8"), "application/json")}
    val_resp = client.post("/packages/validate", headers=teacher_headers, files=files)
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True, f"Validation failed: {val_data}"
    print("Package validation passed: Package structure and cryptographic checksum valid.")

    # 3. Import package to create a replicated exam
    files = {"file": (filename, package_json_str.encode("utf-8"), "application/json")}
    import_resp = client.post("/packages/import", headers=teacher_headers, files=files)
    assert import_resp.status_code == 200, f"Import failed: {import_resp.text}"
    import_data = import_resp.json()
    assert import_data["success"] is True
    new_exam_id = import_data["exam_id"]
    print(f"Package imported into new exam successfully: New Exam ID = {new_exam_id}")
    print(f"  - Questions imported: {import_data['questions_imported']}")

    # 4. Publish package module to school repository
    publish_req = {
        "name": "Physics & Energy Master Module",
        "version": "1.0.0",
        "description": "Standardized high school physics exam package with rubrics and answer keys.",
        "category": "physics",
        "subject": "Physics",
        "grade_level": "Grade 10-12",
        "tags": ["physics", "energy", "mechanics", "newton"],
        "license": "CC-BY-4.0",
        "is_public": True,
        "package_data": package_dict,
    }
    create_pkg_resp = client.post("/packages", headers=teacher_headers, json=publish_req)
    assert create_pkg_resp.status_code == 201, f"Create package failed: {create_pkg_resp.text}"
    created_pkg = create_pkg_resp.json()
    published_pkg_id = created_pkg["id"]
    print(f"Module successfully published to catalog! Package ID: {published_pkg_id}")
    print(f"  - Author: {created_pkg['author']}")
    print(f"  - Category: {created_pkg['category']}")
    print(f"  - Tags: {created_pkg['tags']}")

    # 5. Browse published packages
    browse_resp = client.get("/packages?category=physics&is_public=true", headers=teacher_headers)
    assert browse_resp.status_code == 200
    browse_data = browse_resp.json()
    found = [p for p in browse_data["packages"] if p["id"] == published_pkg_id]
    assert len(found) > 0, "Published package not found in catalog search!"
    print(f"Catalog search verified: Package '{found[0]['name']}' is discoverable by teachers.")

    # 6. Download package
    dl_resp = client.get(f"/packages/{published_pkg_id}/download", headers=teacher_headers)
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()
    assert "content" in dl_data
    print(f"Package download verified: Received file '{dl_data['filename']}' ({len(dl_data['content'])} bytes).")

    # ─────────────────────────────────────────────────────────────────────────────
    # STEP 7: Custom School Source URL Federation & Sync
    # ─────────────────────────────────────────────────────────────────────────────
    print_step("STEP 7: Custom School Source URL Federation & Synchronization")

    # Admin configures external school source URL
    source_payload = {
        "name": "Springfield High School Module Repo",
        "url": f"{BASE_URL}/packages",
        "source_type": "custom",
        "is_enabled": True,
        "is_default": True,
        "auto_sync": True,
        "allowed_categories": ["physics", "mathematics"],
        "allowed_tags": ["high-school", "stem"],
    }
    source_resp = client.post("/packages/sources", headers=admin_headers, json=source_payload)
    assert source_resp.status_code == 201, f"Failed to create source: {source_resp.text}"
    source_obj = source_resp.json()
    source_id = source_obj["id"]
    print(f"Custom package source registered: '{source_obj['name']}' -> {source_obj['url']}")

    # List sources
    sources_list = client.get("/packages/sources", headers=teacher_headers)
    assert sources_list.status_code == 200
    matching_sources = [s for s in sources_list.json() if s["id"] == source_id]
    assert len(matching_sources) > 0
    print("Teachers can list and browse configured school module sources.")

    # Trigger synchronization from custom source
    sync_resp = client.post(f"/packages/sources/{source_id}/sync", headers=admin_headers)
    assert sync_resp.status_code == 200, f"Sync failed: {sync_resp.text}"
    sync_result = sync_resp.json()
    print(f"Source synchronization executed: {sync_result}")
    assert sync_result.get("status") in ("success", "sync_initiated")

    print_step("ALL TESTS PASSED! Native Deployment & End-to-End Workflow 100% Successful!")


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
