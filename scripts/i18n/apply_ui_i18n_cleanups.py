import re

def update_ai_grading():
    path = "web/apps/portal/src/pages/AIGradingUpload.tsx"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add reviewDigitized state
    content = content.replace(
        "const [reviewCorrected, setReviewCorrected] = useState<string>('');\n  const [zoomLevel, setZoomLevel] = useState<number>(1);",
        "const [reviewCorrected, setReviewCorrected] = useState<string>('');\n  const [reviewDigitized, setReviewDigitized] = useState<string>('');\n  const [zoomLevel, setZoomLevel] = useState<number>(1);"
    ).replace(
        "const [reviewCorrected, setReviewCorrected] = useState<string>('');\r\n  const [zoomLevel, setZoomLevel] = useState<number>(1);",
        "const [reviewCorrected, setReviewCorrected] = useState<string>('');\r\n  const [reviewDigitized, setReviewDigitized] = useState<string>('');\r\n  const [zoomLevel, setZoomLevel] = useState<number>(1);"
    )

    # 2. In openReviewModal, setReviewDigitized and catch (_e)
    content = content.replace(
        "    setReviewScore(parsedScore);\n    setReviewFeedback(parsedFeedback);\n    setReviewCorrected(parsedCorrected);\n  };",
        "    setReviewScore(parsedScore);\n    setReviewFeedback(parsedFeedback);\n    setReviewCorrected(parsedCorrected);\n    setReviewDigitized(parsedDigitized);\n  };"
    ).replace(
        "    setReviewScore(parsedScore);\r\n    setReviewFeedback(parsedFeedback);\r\n    setReviewCorrected(parsedCorrected);\r\n  };",
        "    setReviewScore(parsedScore);\r\n    setReviewFeedback(parsedFeedback);\r\n    setReviewCorrected(parsedCorrected);\r\n    setReviewDigitized(parsedDigitized);\r\n  };"
    )

    content = content.replace("} catch (e) {\n        parsedFeedback = sub.feedback;", "} catch (_e) {\n        parsedFeedback = sub.feedback;")
    content = content.replace("} catch (e) {\r\n        parsedFeedback = sub.feedback;", "} catch (_e) {\r\n        parsedFeedback = sub.feedback;")

    # 3. In handleSaveAndApprove catch
    content = content.replace("} catch (err: any) {\n      // Fallback: update status locally", "} catch (_err: any) {\n      // Fallback: update status locally")
    content = content.replace("} catch (err: any) {\r\n      // Fallback: update status locally", "} catch (_err: any) {\r\n      // Fallback: update status locally")

    # 4. In handleApproveAll
    content = content.replace(
        "showSuccess(`${stagedSubs.length} submissions approved!`);",
        "showSuccess(t('ai_grading.submissions_approved_success', { count: String(stagedSubs.length) }));"
    )
    content = content.replace(
        "showError('Error approving submissions', err.message);",
        "showError(t('ai_grading.approve_error'), err.message);"
    )
    content = content.replace("} catch (e) {\n          // ignore individual errors", "} catch (_e) {\n          // ignore individual errors")
    content = content.replace("} catch (e) {\r\n          // ignore individual errors", "} catch (_e) {\r\n          // ignore individual errors")

    # 5. Class roster options
    content = content.replace(
        "{cName} ({classRosters[cName].length} students)",
        "{cName} ({t('ai_grading.students_count', { count: String(classRosters[cName].length) })})"
    )

    # 6. Supported formats description
    content = content.replace(
        "Supports photos from mobile cameras, scans, PNG, JPG, JPEG, and PDF.",
        "{t('ai_grading.supported_formats_desc')}"
    )

    # 7. Modal strings
    content = content.replace(
        "No image photo attached for this submission.",
        "{t('ai_grading.no_image_photo')}"
    )
    content = content.replace(
        "Digitized Extracted Text:",
        "{t('ai_grading.digitized_extracted_text')}"
    )
    content = content.replace(
        "{activeReviewSub.digitized_text || '(No text extracted)'}",
        "{reviewDigitized || t('ai_grading.no_text_extracted')}"
    )
    content = content.replace(
        "Step-by-Step Correct Solution:",
        "{t('ai_grading.step_by_step_solution')}"
    )
    content = content.replace(
        "{t('ai_grading.score_label')} (out of 10):",
        "{t('ai_grading.score_label')} {t('ai_grading.score_out_of_10')}"
    )
    content = content.replace(
        "['Great work!', 'Check algebra in step 2', 'Review physical units', 'Clear derivation', 'Partial credit']",
        "[t('ai_grading.chip_great_work'), t('ai_grading.chip_check_algebra'), t('ai_grading.chip_review_units'), t('ai_grading.chip_clear_derivation'), t('ai_grading.chip_partial_credit')]"
    )
    content = content.replace(
        ">Cancel</button>",
        ">{t('common.cancel')}</button>"
    ).replace(
        ">\n                Cancel\n              </button>",
        ">\n                {t('common.cancel')}\n              </button>"
    ).replace(
        ">\r\n                Cancel\r\n              </button>",
        ">\r\n                {t('common.cancel')}\r\n              </button>"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated AIGradingUpload.tsx")

def update_student_dashboard():
    path = "web/apps/portal/src/pages/StudentDashboard.tsx"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("} catch (e) {}", "} catch (_e) {}")
    content = content.replace(
        "{sub.score !== null ? `${sub.score} / 10 pts` : 'Graded'}",
        "{sub.score !== null ? t('student_dashboard.score_pts', { score: String(sub.score) }) : t('student_dashboard.graded')}"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated StudentDashboard.tsx")

def update_parent_dashboard():
    path = "web/apps/portal/src/pages/ParentDashboard.tsx"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("} catch (e) {}", "} catch (_e) {}")
    content = content.replace(
        "let displayFb = exam.feedback || 'No feedback recorded yet.';",
        "let displayFb = exam.feedback || t('parent.no_feedback');"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated ParentDashboard.tsx")

def update_api_client():
    path = "web/apps/portal/src/api.ts"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "apiClient.interceptors.response.use" not in content:
        interceptor_code = """
// Intercept 401s to clear stale access tokens and avoid repetitive unauthorized requests
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        localStorage.removeItem('access_token');
      }
    }
    return Promise.reject(error);
  }
);
"""
        content += interceptor_code
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated api.ts with 401 response interceptor")

update_ai_grading()
update_student_dashboard()
update_parent_dashboard()
update_api_client()

