from collections import Counter


EVENT_RULES = {
    "face_missing": {"score": 22, "warning": 1, "severity": "high"},
    "multi_face": {"score": 30, "warning": 1, "severity": "critical"},
    "gaze_left": {"score": 8, "warning": 0, "severity": "medium"},
    "gaze_right": {"score": 8, "warning": 0, "severity": "medium"},
    "gaze_down": {"score": 10, "warning": 0, "severity": "medium"},
    "tab_switch": {"score": 18, "warning": 1, "severity": "high"},
    "audio_alert": {"score": 16, "warning": 1, "severity": "high"},
    "object_detected": {"score": 26, "warning": 1, "severity": "critical"},
}


def score_monitor_event(current_warnings, current_score, event_type, detail):
    """Apply simple transparent rules to convert events into suspicion metrics."""
    rule = EVENT_RULES.get(event_type, {"score": 5, "warning": 0, "severity": "low"})
    new_warning_count = current_warnings + rule["warning"]
    new_score = min(100, current_score + rule["score"])
    cheating_flag = new_warning_count >= 3 or new_score >= 70 or event_type == "multi_face"
    return {
        "warning_count": new_warning_count,
        "suspicion_score": new_score,
        "cheating_flag": cheating_flag,
        "severity": rule["severity"],
        "message": f"{event_type.replace('_', ' ').title()} detected: {detail or 'No detail provided'}",
    }


def build_exam_report(exam_session, events):
    """Build a summary dictionary that templates can render as a report."""
    event_counter = Counter(event["event_type"] for event in events)
    risk_level = "Low"
    if exam_session["cheating_flag"]:
        risk_level = "Critical"
    elif exam_session["suspicion_score"] >= 40:
        risk_level = "Moderate"

    return {
        "risk_level": risk_level,
        "event_counter": event_counter,
        "summary": [
            f"Warnings issued: {exam_session['warning_count']}",
            f"Suspicion score: {exam_session['suspicion_score']} / 100",
            f"Most frequent event: {event_counter.most_common(1)[0][0] if event_counter else 'none'}",
        ],
        "cnn_ready_note": "Project structure is ready for a Kaggle-backed object detector such as YOLO or MobileNet transfer learning.",
    }


def compute_dashboard_metrics(db, user_id=None):
    """Aggregate headline metrics for either one user or the full platform."""
    if user_id:
        total_sessions = db.execute("SELECT COUNT(*) AS count FROM exam_sessions WHERE user_id = ?", (user_id,)).fetchone()["count"]
        flagged_sessions = db.execute(
            "SELECT COUNT(*) AS count FROM exam_sessions WHERE user_id = ? AND cheating_flag = 1",
            (user_id,),
        ).fetchone()["count"]
        total_uploads = db.execute("SELECT COUNT(*) AS count FROM uploads WHERE user_id = ?", (user_id,)).fetchone()["count"]
        total_messages = db.execute("SELECT COUNT(*) AS count FROM messages WHERE user_id = ?", (user_id,)).fetchone()["count"]
        return {
            "total_sessions": total_sessions,
            "flagged_sessions": flagged_sessions,
            "total_uploads": total_uploads,
            "total_messages": total_messages,
        }

    total_users = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    total_sessions = db.execute("SELECT COUNT(*) AS count FROM exam_sessions").fetchone()["count"]
    flagged_sessions = db.execute("SELECT COUNT(*) AS count FROM exam_sessions WHERE cheating_flag = 1").fetchone()["count"]
    total_contacts = db.execute("SELECT COUNT(*) AS count FROM contact_messages").fetchone()["count"]
    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "flagged_sessions": flagged_sessions,
        "total_contacts": total_contacts,
    }
