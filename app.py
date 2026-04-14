import sys
sys.dont_write_bytecode = True

from datetime import datetime
from pathlib import Path
import sqlite3

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from ai_utils import build_exam_report, compute_dashboard_metrics, score_monitor_event
from models import init_db


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = "file:proctorai_demo?mode=memory&cache=shared"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_KEEPER = None

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-me"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ARTICLES = [
    {
        "title": "AI Proctoring Reduced Review Time by 42%",
        "summary": "Recruiting teams cut manual review effort by combining tab events, face checks, and rule-based suspicion scoring.",
    },
    {
        "title": "Structured Alerts Helped Faster Interview Decisions",
        "summary": "Live warnings and timeline reports made it easier to defend OA screening outcomes with clean evidence.",
    },
    {
        "title": "Simple Models Can Still Be Effective",
        "summary": "Using lightweight OpenCV, MediaPipe, and pretrained CNN hooks keeps the system explainable for demos and viva rounds.",
    },
]

TESTIMONIALS = [
    {
        "name": "Priya Sharma",
        "role": "Campus Hiring Lead",
        "quote": "The dashboard made suspicious sessions easy to review without needing a giant manual audit team.",
    },
    {
        "name": "Arjun Patel",
        "role": "Placement Coordinator",
        "quote": "It looked modern enough to impress stakeholders, but the logic stayed simple enough for students to explain.",
    },
    {
        "name": "Neha Gupta",
        "role": "Assessment Admin",
        "quote": "The report timeline and warning counter were the most useful parts during candidate verification.",
    },
]

FEATURES = [
    "Face presence and multi-face detection",
    "Gaze deviation scoring for attention tracking",
    "Tab switch and page visibility monitoring",
    "Audio activity warnings",
    "Dataset-ready object detection pipeline",
    "Live dashboard, reports, payments, uploads, and messaging",
]


def get_db():
    """Return a SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH, uri=True)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.before_request
def ensure_setup():
    """Create required storage assets before handling requests."""
    global DB_KEEPER
    if DB_KEEPER is None:
        DB_KEEPER = init_db(DATABASE_PATH)
        seed_defaults()
    UPLOAD_DIR.mkdir(exist_ok=True)
    ensure_question_bank()


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def current_user():
    """Return the current logged-in user row if available."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required():
    """Redirect anonymous users to the login page."""
    if not current_user():
        flash("Please log in to continue.", "warning")
        return redirect(url_for("login"))
    return None


def admin_required():
    """Redirect non-admin users away from admin pages."""
    user = current_user()
    if not user or user["role"] != "admin":
        flash("Admin access is required.", "danger")
        return redirect(url_for("dashboard"))
    return None


def create_exam_session(user_id):
    """Create a new exam session with default counters."""
    db = get_db()
    db.execute(
        """
        INSERT INTO exam_sessions (user_id, exam_title, status, warning_count, suspicion_score, cheating_flag, created_at)
        VALUES (?, ?, 'active', 0, 0, 0, ?)
        """,
        (user_id, "AI Integrity Screening", datetime.utcnow().isoformat()),
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def ensure_question_bank():
    """Create starter questions so each user can get a personal exam set."""
    db = get_db()
    total_questions = db.execute("SELECT COUNT(*) AS count FROM questions").fetchone()["count"]
    if total_questions:
        return

    starter_questions = [
        (
            "Design a secure OA workflow",
            "Explain how webcam checks, tab-switch detection, and suspicion scoring should work together in an online assessment.",
            "Medium",
        ),
        (
            "Handling suspicious behavior",
            "What should happen when a candidate repeatedly looks away or another face appears on screen during an interview?",
            "Medium",
        ),
        (
            "Fairness in AI proctoring",
            "Describe how an anti-cheating system can stay transparent, reviewable, and fair for candidates.",
            "Hard",
        ),
    ]
    for title, body, difficulty in starter_questions:
        db.execute(
            """
            INSERT INTO questions (title, body, difficulty, created_by, created_at)
            VALUES (?, ?, ?, NULL, ?)
            """,
            (title, body, difficulty, datetime.utcnow().isoformat()),
        )
    db.commit()


def assign_default_questions(user_id):
    """Assign starter questions to a user who has no questions yet."""
    db = get_db()
    assigned_count = db.execute(
        "SELECT COUNT(*) AS count FROM user_questions WHERE user_id = ?",
        (user_id,),
    ).fetchone()["count"]
    if assigned_count:
        return

    question_ids = db.execute("SELECT id FROM questions ORDER BY id LIMIT 3").fetchall()
    for row in question_ids:
        db.execute(
            """
            INSERT INTO user_questions (user_id, question_id, status, created_at)
            VALUES (?, ?, 'assigned', ?)
            """,
            (user_id, row["id"], datetime.utcnow().isoformat()),
        )
    db.commit()


def get_user_questions(user_id):
    """Return all questions assigned to a specific user."""
    db = get_db()
    return db.execute(
        """
        SELECT user_questions.id AS assignment_id, user_questions.status, questions.title, questions.body, questions.difficulty
        FROM user_questions
        JOIN questions ON questions.id = user_questions.question_id
        WHERE user_questions.user_id = ?
        ORDER BY user_questions.id
        """,
        (user_id,),
    ).fetchall()


def seed_defaults():
    """Insert a default admin user so the demo is easier to explore."""
    db = sqlite3.connect(DATABASE_PATH, uri=True)
    user = db.execute("SELECT id FROM users WHERE email = ?", ("admin@proctoraix.com",)).fetchone()
    if not user:
        db.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, 'admin', ?)
            """,
            ("Platform Admin", "admin@proctoraix.com", generate_password_hash("admin123"), datetime.utcnow().isoformat()),
        )
        db.commit()
    db.close()


@app.route("/")
def home():
    """Render the public landing page with feature and trust content."""
    metrics = compute_dashboard_metrics(get_db())
    return render_template(
        "home.html",
        user=current_user(),
        articles=ARTICLES,
        testimonials=TESTIMONIALS,
        features=FEATURES,
        metrics=metrics,
    )


@app.route("/about")
def about():
    """Show the product story and technology overview."""
    return render_template("about.html", user=current_user())


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Capture contact requests from users or evaluators."""
    if request.method == "POST":
        db = get_db()
        db.execute(
            """
            INSERT INTO contact_messages (name, email, subject, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.form["name"],
                request.form["email"],
                request.form["subject"],
                request.form["message"],
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        flash("Your message has been sent.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html", user=current_user())


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new candidate account in the system."""
    if request.method == "POST":
        db = get_db()
        email = request.form["email"].strip().lower()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))

        db.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, 'student', ?)
            """,
            (
                request.form["name"],
                email,
                generate_password_hash(request.form["password"]),
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        new_user_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        assign_default_questions(new_user_id)
        flash("Registration complete. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a user and store the session."""
    if request.method == "POST":
        db = get_db()
        email = request.form["email"].strip().lower()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], request.form["password"]):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        flash("Welcome back.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html", user=current_user())


@app.route("/logout")
def logout():
    """Clear the current login session."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    """Show the candidate dashboard with sessions, uploads, and messages."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    db = get_db()
    user = current_user()
    sessions = db.execute(
        "SELECT * FROM exam_sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()
    uploads = db.execute(
        "SELECT * FROM uploads WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user["id"],),
    ).fetchall()
    messages = db.execute(
        "SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user["id"],),
    ).fetchall()
    assigned_questions = get_user_questions(user["id"])
    return render_template(
        "dashboard.html",
        user=user,
        exam_sessions=sessions,
        uploads=uploads,
        messages=messages,
        assigned_questions=assigned_questions,
        metrics=compute_dashboard_metrics(db, user["id"]),
    )


@app.route("/exam")
def exam():
    """Start an exam session and render the monitoring interface."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    user = current_user()
    db = get_db()
    user_questions = get_user_questions(user["id"])
    if not user_questions:
        flash("No questions are assigned to this user yet. Please ask the admin to assign questions.", "warning")
        return redirect(url_for("dashboard"))

    active_session = db.execute(
        "SELECT * FROM exam_sessions WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    if not active_session:
        session_id = create_exam_session(user["id"])
        active_session = db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    return render_template("exam.html", user=user, exam_session=active_session, questions=user_questions)


@app.route("/api/monitor", methods=["POST"])
def monitor_event():
    """Receive browser or detection events and update the session counters."""
    redirect_response = login_required()
    if redirect_response:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(force=True)
    db = get_db()
    exam_session = db.execute(
        "SELECT * FROM exam_sessions WHERE id = ?",
        (payload["session_id"],),
    ).fetchone()
    if not exam_session:
        return jsonify({"error": "Session not found"}), 404

    outcome = score_monitor_event(
        exam_session["warning_count"],
        exam_session["suspicion_score"],
        payload.get("event_type", "unknown"),
        payload.get("detail", ""),
    )

    db.execute(
        """
        INSERT INTO monitoring_events (session_id, event_type, detail, severity, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            exam_session["id"],
            payload.get("event_type"),
            payload.get("detail"),
            outcome["severity"],
            datetime.utcnow().isoformat(),
        ),
    )
    db.execute(
        """
        UPDATE exam_sessions
        SET warning_count = ?, suspicion_score = ?, cheating_flag = ?, status = ?
        WHERE id = ?
        """,
        (
            outcome["warning_count"],
            outcome["suspicion_score"],
            1 if outcome["cheating_flag"] else 0,
            "flagged" if outcome["cheating_flag"] else "active",
            exam_session["id"],
        ),
    )
    db.commit()
    return jsonify(outcome)


@app.route("/submit_exam/<int:session_id>", methods=["POST"])
def submit_exam(session_id):
    """Close an exam session and route the user to the result page."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    db = get_db()
    exam_session = db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    if not exam_session:
        flash("Exam session was not found.", "danger")
        return redirect(url_for("dashboard"))

    user_questions = get_user_questions(exam_session["user_id"])
    for question in user_questions:
        answer_text = request.form.get(f"answer_{question['assignment_id']}", "").strip()
        if not answer_text:
            continue

        db.execute(
            """
            INSERT INTO exam_answers (session_id, user_question_id, answer_text, submitted_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, question["assignment_id"], answer_text, datetime.utcnow().isoformat()),
        )
        db.execute(
            "UPDATE user_questions SET status = 'answered' WHERE id = ?",
            (question["assignment_id"],),
        )
    db.execute("UPDATE exam_sessions SET status = 'completed' WHERE id = ?", (session_id,))
    db.commit()
    flash("Exam submitted successfully.", "success")
    return redirect(url_for("results", session_id=session_id))


@app.route("/results/<int:session_id>")
def results(session_id):
    """Show the final report for a completed or flagged exam session."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    db = get_db()
    exam_session = db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    events = db.execute(
        "SELECT * FROM monitoring_events WHERE session_id = ? ORDER BY created_at DESC",
        (session_id,),
    ).fetchall()
    answers = db.execute(
        """
        SELECT questions.title, exam_answers.answer_text
        FROM exam_answers
        JOIN user_questions ON user_questions.id = exam_answers.user_question_id
        JOIN questions ON questions.id = user_questions.question_id
        WHERE exam_answers.session_id = ?
        ORDER BY exam_answers.id
        """,
        (session_id,),
    ).fetchall()
    report = build_exam_report(exam_session, events)
    return render_template(
        "results.html",
        user=current_user(),
        exam_session=exam_session,
        events=events,
        report=report,
        answers=answers,
    )


@app.route("/uploads", methods=["GET", "POST"])
def uploads():
    """Store candidate files such as resume, ID proof, or supporting documents."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    user = current_user()
    db = get_db()
    if request.method == "POST":
        file = request.files.get("document")
        if not file or not file.filename:
            flash("Please choose a file to upload.", "danger")
            return redirect(url_for("uploads"))

        filename = secure_filename(file.filename)
        saved_path = UPLOAD_DIR / filename
        file.save(saved_path)
        db.execute(
            """
            INSERT INTO uploads (user_id, filename, category, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user["id"], filename, request.form["category"], datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("File uploaded.", "success")
        return redirect(url_for("uploads"))

    items = db.execute("SELECT * FROM uploads WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return render_template("uploads.html", user=user, items=items)


@app.route("/payments", methods=["GET", "POST"])
def payments():
    """Capture demo payments for exam enrollment or premium review."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    user = current_user()
    db = get_db()
    if request.method == "POST":
        amount = float(request.form["amount"])
        db.execute(
            """
            INSERT INTO payments (user_id, plan_name, amount, status, created_at)
            VALUES (?, ?, ?, 'paid', ?)
            """,
            (user["id"], request.form["plan_name"], amount, datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("Demo payment recorded successfully.", "success")
        return redirect(url_for("payments"))

    items = db.execute("SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return render_template("payments.html", user=user, items=items)


@app.route("/messages", methods=["GET", "POST"])
def messages():
    """Allow candidates to exchange messages with the platform team."""
    redirect_response = login_required()
    if redirect_response:
        return redirect_response

    user = current_user()
    db = get_db()
    if request.method == "POST":
        db.execute(
            """
            INSERT INTO messages (user_id, sender, subject, body, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                "student",
                request.form["subject"],
                request.form["body"],
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        flash("Message sent to support.", "success")
        return redirect(url_for("messages"))

    rows = db.execute("SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return render_template("messages.html", user=user, messages=rows)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    """Show the admin overview with users, sessions, and contact queue."""
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    db = get_db()
    if request.method == "POST":
        user_id = int(request.form["user_id"])
        title = request.form["title"].strip()
        body = request.form["body"].strip()
        difficulty = request.form["difficulty"]

        db.execute(
            """
            INSERT INTO questions (title, body, difficulty, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, body, difficulty, current_user()["id"], datetime.utcnow().isoformat()),
        )
        question_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        db.execute(
            """
            INSERT INTO user_questions (user_id, question_id, status, created_at)
            VALUES (?, ?, 'assigned', ?)
            """,
            (user_id, question_id, datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("Question assigned to the selected user.", "success")
        return redirect(url_for("admin"))

    return render_template(
        "admin.html",
        user=current_user(),
        users=db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall(),
        sessions=db.execute("SELECT * FROM exam_sessions ORDER BY created_at DESC").fetchall(),
        contacts=db.execute("SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 8").fetchall(),
        assignments=db.execute(
            """
            SELECT users.name, questions.title, user_questions.status
            FROM user_questions
            JOIN users ON users.id = user_questions.user_id
            JOIN questions ON questions.id = user_questions.question_id
            ORDER BY user_questions.id DESC
            LIMIT 8
            """
        ).fetchall(),
        metrics=compute_dashboard_metrics(db),
    )


@app.route("/seed_reply/<int:user_id>", methods=["POST"])
def seed_reply(user_id):
    """Create a simple admin response to keep the messaging flow demonstrable."""
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    db = get_db()
    db.execute(
        """
        INSERT INTO messages (user_id, sender, subject, body, created_at)
        VALUES (?, 'admin', ?, ?, ?)
        """,
        (user_id, request.form["subject"], request.form["body"], datetime.utcnow().isoformat()),
    )
    db.commit()
    flash("Admin reply sent.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    DB_KEEPER = init_db(DATABASE_PATH)
    UPLOAD_DIR.mkdir(exist_ok=True)
    seed_defaults()
    app.run(debug=True)
