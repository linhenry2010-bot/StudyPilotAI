import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO


try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


# =====================
# PAGE CONFIG + STYLE
# =====================

st.set_page_config(
    page_title="StudyPilot AI V4",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 40%, #dbeafe 100%);
    color: #1e293b;
}

section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(18px);
    border-right: 1px solid #dbeafe;
}

.main-title {
    font-size: 56px;
    font-weight: 900;
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}

.subtitle {
    color: #475569 !important;
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 28px;
}

label,
.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stDateInput label,
.stSlider label,
.stRadio label {
    color: #1e293b !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
    background: rgba(255,255,255,0.96) !important;
    color: #111827 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
}

/* ===== FIX ALL BUTTONS ===== */

.stButton button,
.stFormSubmitButton button,
button[kind="primary"] {

    background: linear-gradient(
        135deg,
        #6366f1,
        #8b5cf6
    ) !important;

    color: white !important;

    border: none !important;

    border-radius: 16px !important;

    font-weight: 700 !important;

    font-size: 16px !important;

    height: 50px !important;

    width: 100% !important;

    box-shadow: 0 8px 20px rgba(99,102,241,0.35) !important;
}

.stButton button *,
.stFormSubmitButton button *,
button[kind="primary"] * {
    color: white !important;
}

.stButton button:hover,
.stFormSubmitButton button:hover,
button[kind="primary"]:hover {

    transform: translateY(-2px);

    transition: 0.2s ease;

    box-shadow: 0 14px 30px rgba(99,102,241,0.45) !important;
}

.card,
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.88) !important;
    backdrop-filter: blur(16px);
    border-radius: 22px !important;
    border: 1px solid rgba(255,255,255,0.7) !important;
    box-shadow: 0 10px 28px rgba(15,23,42,0.08);
    color: #1e293b !important;
}

div[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 10px 28px rgba(15,23,42,0.08);
}

h1, h2, h3, h4, p, span {
    color: #1e293b;
}

.high-risk {
    padding: 8px 12px;
    border-radius: 999px;
    background-color: #fee2e2;
    color: #991b1b;
    font-weight: 800;
}

.medium-risk {
    padding: 8px 12px;
    border-radius: 999px;
    background-color: #fef3c7;
    color: #92400e;
    font-weight: 800;
}

.low-risk {
    padding: 8px 12px;
    border-radius: 999px;
    background-color: #dcfce7;
    color: #166534;
    font-weight: 800;
}

/* Download button */

.stDownloadButton button,
.stDownloadButton button * {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    height: 50px !important;
    box-shadow: 0 8px 20px rgba(99,102,241,0.35) !important;
}

</style>
""", unsafe_allow_html=True)

# =====================
# DATABASE
# =====================

conn = sqlite3.connect("studypilot_v4.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS assignments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    name TEXT,
    subject TEXT,
    hours REAL,
    difficulty INTEGER,
    due_date TEXT,
    completed INTEGER DEFAULT 0,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS exams(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    exam_name TEXT,
    subject TEXT,
    exam_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS study_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    subject TEXT,
    minutes INTEGER,
    log_date TEXT,
    notes TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS survey_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    student_name TEXT,
    grade_level TEXT,
    ease_of_use INTEGER,
    usefulness INTEGER,
    would_recommend INTEGER,
    feedback TEXT,
    created_at TEXT
)
""")

conn.commit()


# =====================
# HELPER FUNCTIONS
# =====================

def hash_password(password):
    return sha256(password.encode()).hexdigest()


def register(username, password):
    try:
        cursor.execute(
            "INSERT INTO users(username, password, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), str(datetime.now()))
        )
        conn.commit()
        return True
    except Exception:
        return False


def login(username, password):
    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    return cursor.fetchone()


def get_assignments(username):
    cursor.execute("""
    SELECT id, name, subject, hours, difficulty, due_date, completed
    FROM assignments
    WHERE username=?
    """, (username,))
    return cursor.fetchall()


def assignment_dataframe(username):
    data = get_assignments(username)

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(
        data,
        columns=[
            "ID",
            "Assignment",
            "Subject",
            "Hours",
            "Difficulty",
            "Due Date",
            "Completed"
        ]
    )

    df["Due Date"] = pd.to_datetime(df["Due Date"])
    today = pd.Timestamp.today().normalize()
    df["Days Left"] = (df["Due Date"] - today).dt.days

    df["Urgency"] = df["Days Left"].apply(
        lambda x: 10 if x <= 0 else max(1, 10 - x)
    )

    df["Priority Score"] = (
        df["Difficulty"] * 3 +
        df["Hours"] * 2 +
        df["Urgency"] * 2
    )

    df["Risk Level"] = df["Priority Score"].apply(
        lambda x: "High" if x >= 30 else ("Medium" if x >= 20 else "Low")
    )

    df["Status"] = df["Completed"].apply(
        lambda x: "Done" if x == 1 else "Not Done"
    )

    return df


def calculate_needed_score(current, final_weight, target):
    weight = final_weight / 100

    if weight == 0:
        return 0

    return (target - current * (1 - weight)) / weight


def letter_from_gpa(gpa):
    if gpa >= 3.7:
        return "A / A- Range"
    elif gpa >= 3.3:
        return "B+ Range"
    elif gpa >= 3.0:
        return "B Range"
    elif gpa >= 2.7:
        return "B- Range"
    elif gpa >= 2.3:
        return "C+ Range"
    elif gpa >= 2.0:
        return "C Range"
    else:
        return "Below C Range"


def generate_rule_based_advice(df, workload_text):
    if df.empty:
        return "Add assignments first so StudyPilot can create a better plan."

    unfinished = df[df["Completed"] == 0]

    if unfinished.empty:
        return "All assignments are completed. Great job."

    priority = unfinished.sort_values("Priority Score", ascending=False).head(5)
    top = priority.iloc[0]

    advice = []
    advice.append("Recommended Study Plan:")
    advice.append("")

    for i, (_, row) in enumerate(priority.iterrows(), start=1):
        advice.append(
            f"{i}. {row['Assignment']} — {row['Subject']} | "
            f"{row['Hours']} hours | Due in {row['Days Left']} days | "
            f"Risk: {row['Risk Level']}"
        )

    advice.append("")
    advice.append("Main Recommendation:")

    if top["Days Left"] <= 1:
        advice.append(f"Focus on {top['Assignment']} first because it is due very soon.")
    elif top["Risk Level"] == "High":
        advice.append(f"Break {top['Assignment']} into smaller study sessions.")
    else:
        advice.append("Start with the highest priority task, then review your hardest subject.")

    advice.append("")
    advice.append("Suggested Strategy:")
    advice.append("Use 45-minute focus blocks.")
    advice.append("Take short breaks between sessions.")
    advice.append("Review difficult subjects a little each day.")
    advice.append("Do not leave large assignments until the last night.")

    if workload_text:
        advice.append("")
        advice.append("Based on your note:")
        advice.append(workload_text)

    return "\n".join(advice)


def generate_openai_advice(df, workload_text):
    api_key = st.secrets.get("OPENAI_API_KEY", "")

    if not api_key or not OPENAI_AVAILABLE:
        return None

    client = OpenAI(api_key=api_key)

    tasks_text = "No assignments."
    if not df.empty:
        tasks_text = df.sort_values("Priority Score", ascending=False)[
            ["Assignment", "Subject", "Hours", "Difficulty", "Days Left", "Priority Score", "Risk Level", "Status"]
        ].to_string(index=False)

    prompt = f"""
You are StudyPilot AI, a student study planning assistant.
Create a practical 3-day study plan for a high school student.

Assignments:
{tasks_text}

Student note:
{workload_text}

Rules:
- Be specific.
- Prioritize urgent and high-risk tasks.
- Keep advice healthy and realistic.
- Do not give medical advice.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You help students plan homework and studying safely and realistically."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def create_pdf_report(username):
    df = assignment_dataframe(username)
    buffer = BytesIO()

    if not REPORTLAB_AVAILABLE:
        text = create_text_report(username)
        buffer.write(text.encode("utf-8"))
        buffer.seek(0)
        return buffer

    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "StudyPilot AI V4 Weekly Report")

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Student: {username}")
    y -= 18
    c.drawString(50, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y -= 35

    if df.empty:
        c.drawString(50, y, "No assignment data yet.")
    else:
        total_tasks = len(df)
        total_hours = round(df["Hours"].sum(), 1)
        completed_tasks = int(df["Completed"].sum())
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)
        high_risk = len(df[df["Risk Level"] == "High"])

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Summary")
        y -= 22

        c.setFont("Helvetica", 11)
        summary_lines = [
            f"Total Assignments: {total_tasks}",
            f"Total Estimated Study Hours: {total_hours}",
            f"Completed Assignments: {completed_tasks}",
            f"Completion Rate: {completion_rate}%",
            f"High Risk Tasks: {high_risk}",
        ]

        for line in summary_lines:
            c.drawString(60, y, line)
            y -= 18

        y -= 15
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Top Priority Tasks")
        y -= 22

        c.setFont("Helvetica", 10)

        top_tasks = df.sort_values("Priority Score", ascending=False).head(8)

        for _, row in top_tasks.iterrows():
            line = (
                f"{row['Assignment']} | {row['Subject']} | "
                f"Priority: {row['Priority Score']} | Risk: {row['Risk Level']} | "
                f"Due: {row['Due Date'].date()}"
            )
            c.drawString(60, y, line[:95])
            y -= 16

            if y < 70:
                c.showPage()
                y = height - 50

    c.save()
    buffer.seek(0)
    return buffer


def create_text_report(username):
    df = assignment_dataframe(username)
    report = []
    report.append("StudyPilot AI V4 Weekly Report")
    report.append("==============================")
    report.append(f"Student: {username}")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    if df.empty:
        report.append("No assignment data yet.")
    else:
        total_tasks = len(df)
        total_hours = round(df["Hours"].sum(), 1)
        completed_tasks = int(df["Completed"].sum())
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)

        report.append(f"Total Assignments: {total_tasks}")
        report.append(f"Total Estimated Study Hours: {total_hours}")
        report.append(f"Completed Assignments: {completed_tasks}")
        report.append(f"Completion Rate: {completion_rate}%")
        report.append("")

        report.append("Top Priority Tasks:")

        top_tasks = df.sort_values("Priority Score", ascending=False).head(5)

        for _, row in top_tasks.iterrows():
            report.append(
                f"- {row['Assignment']} | {row['Subject']} | "
                f"Priority: {row['Priority Score']} | Risk: {row['Risk Level']} | "
                f"Due: {row['Due Date'].date()}"
            )

    return "\n".join(report)


def risk_badge(level):
    if level == "High":
        return '<span class="high-risk">High Risk</span>'
    elif level == "Medium":
        return '<span class="medium-risk">Medium Risk</span>'
    return '<span class="low-risk">Low Risk</span>'


# =====================
# AUTH PAGE
# =====================

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown('<div class="main-title">📚 StudyPilot AI V4</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">An AI-powered academic planning platform for high school students.</div>', unsafe_allow_html=True)

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with register_tab:
        st.subheader("Create Account")
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Register Account"):
            if new_user and new_pass:
                success = register(new_user, new_pass)
                if success:
                    st.success("Account created successfully. Now login.")
                else:
                    st.error("Username already exists.")
            else:
                st.warning("Please complete all fields.")

    st.stop()


# =====================
# SIDEBAR
# =====================

st.sidebar.success(f"Logged in as {st.session_state.user}")

page = st.sidebar.selectbox(
    "Menu",
    [
        "Dashboard",
        "Homework Planner",
        "Grade Recovery Calculator",
        "Study Analytics",
        "AI Advisor",
        "AP Countdown",
        "Study Tracker",
        "Weekly Report PDF",
        "User Testing Survey",
        "Project Info"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()


# =====================
# DASHBOARD
# =====================

if page == "Dashboard":
    st.markdown('<div class="main-title">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your academic command center.</div>', unsafe_allow_html=True)

    df = assignment_dataframe(st.session_state.user)

    if df.empty:
        st.info("No assignments yet. Add tasks in Homework Planner.")
    else:
        total_tasks = len(df)
        total_hours = round(df["Hours"].sum(), 1)
        completed_tasks = int(df["Completed"].sum())
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)
        high_risk_tasks = len(df[df["Risk Level"] == "High"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tasks", total_tasks)
        col2.metric("Study Hours", total_hours)
        col3.metric("Completion Rate", f"{completion_rate}%")
        col4.metric("High Risk Tasks", high_risk_tasks)

        st.subheader("Top Priority Tasks")
        top_tasks = df.sort_values("Priority Score", ascending=False).head(5)

        st.dataframe(
            top_tasks[
                [
                    "Assignment",
                    "Subject",
                    "Hours",
                    "Difficulty",
                    "Days Left",
                    "Priority Score",
                    "Risk Level",
                    "Status"
                ]
            ],
            use_container_width=True
        )

        highest = top_tasks.iloc[0]
        st.subheader("Quick Recommendation")

        st.markdown(
            f"""
<div class="card">
<b>Start with:</b> {highest['Assignment']}<br>
<b>Subject:</b> {highest['Subject']}<br>
<b>Risk:</b> {risk_badge(highest['Risk Level'])}<br>
<b>Reason:</b> This task has the highest priority score.
</div>
""",
            unsafe_allow_html=True
        )

        st.subheader("Hours by Subject")
        st.bar_chart(df.groupby("Subject")["Hours"].sum())


# =====================
# HOMEWORK PLANNER
# =====================


elif page == "Homework Planner":

    st.markdown("""
<div class="main-title">
📝 Homework Planner
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="subtitle">
Plan smarter. Stress less.
</div>
""", unsafe_allow_html=True)
    with st.form("assignment_form"):
        name = st.text_input("Assignment Name")
        subject = st.text_input("Subject")
        hours = st.number_input(
            "Estimated Hours",
            min_value=0.5,
            max_value=50.0,
            value=2.0,
            step=0.5
        )
        difficulty = st.slider("Difficulty", 1, 5, 3)
        due_date = st.date_input("Due Date", min_value=date.today())
        submit = st.form_submit_button("Add Assignment")

    if submit:
        if name and subject:
            cursor.execute("""
            INSERT INTO assignments(
                username,
                name,
                subject,
                hours,
                difficulty,
                due_date,
                completed,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """, (
                st.session_state.user,
                name,
                subject,
                hours,
                difficulty,
                str(due_date),
                0,
                str(datetime.now())
            ))
            conn.commit()
            st.success("Assignment added.")
        else:
            st.warning("Please enter assignment name and subject.")

    df = assignment_dataframe(st.session_state.user)

    if df.empty:
        st.info("No assignments yet.")
    else:
        st.subheader("Your Assignments")

        display_df = df.sort_values("Priority Score", ascending=False)

        st.dataframe(
            display_df[
                [
                    "ID",
                    "Assignment",
                    "Subject",
                    "Hours",
                    "Difficulty",
                    "Due Date",
                    "Days Left",
                    "Priority Score",
                    "Risk Level",
                    "Status"
                ]
            ],
            use_container_width=True
        )

        st.subheader("Update Assignment")
        selected_id = st.number_input("Enter Assignment ID", min_value=1, step=1)
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Mark as Completed"):
                cursor.execute(
                    "UPDATE assignments SET completed=1 WHERE id=? AND username=?",
                    (selected_id, st.session_state.user)
                )
                conn.commit()
                st.success("Marked as completed.")
                st.rerun()

        with col2:
            if st.button("Mark as Not Done"):
                cursor.execute(
                    "UPDATE assignments SET completed=0 WHERE id=? AND username=?",
                    (selected_id, st.session_state.user)
                )
                conn.commit()
                st.success("Marked as not done.")
                st.rerun()

        with col3:
            if st.button("Delete Assignment"):
                cursor.execute(
                    "DELETE FROM assignments WHERE id=? AND username=?",
                    (selected_id, st.session_state.user)
                )
                conn.commit()
                st.success("Assignment deleted.")
                st.rerun()


# =====================
# GRADE RECOVERY
# =====================

elif page == "Grade Recovery Calculator":
    st.header("🎯 Grade Recovery Calculator V4")

    calculator_type = st.radio(
        "Select Calculator",
        [
            "Percentage Grade",
            "4.0 GPA Scale"
        ]
    )

    if calculator_type == "Percentage Grade":
        current_grade = st.number_input("Current Grade (%)", 0.0, 100.0, 85.0)
        final_weight = st.slider("Final Weight (%)", 1, 60, 20)
        target_grade = st.number_input("Target Grade (%)", 0.0, 100.0, 90.0)

        if st.button("Calculate Required Final Score"):
            needed = calculate_needed_score(current_grade, final_weight, target_grade)

            if needed > 100:
                st.error(f"You need {needed:.2f}% on the final. This may not be achievable.")
            elif needed < 0:
                st.success("You have already reached your target grade.")
            else:
                st.success(f"You need {needed:.2f}% on the final.")

    else:
        current_gpa = st.number_input("Current GPA", 0.0, 4.0, 2.93)
        final_weight = st.slider("Final Weight (%)", 1, 60, 16)
        target_gpa = st.number_input("Target GPA", 0.0, 4.0, 3.00)

        if st.button("Calculate Required GPA Performance"):
            needed = calculate_needed_score(current_gpa, final_weight, target_gpa)

            st.write(f"Required final performance: **{needed:.2f} GPA level**")
            st.write(f"Equivalent Grade Range: **{letter_from_gpa(needed)}**")

            if needed > 4.0:
                st.error("This target may not be possible through the final alone.")
            elif needed <= current_gpa:
                st.success("You are already close to your target.")
            else:
                st.success("Your target appears achievable with a strong final performance.")


# =====================
# ANALYTICS
# =====================

elif page == "Study Analytics":
    st.header("📊 Study Analytics V4")

    df = assignment_dataframe(st.session_state.user)

    if df.empty:
        st.info("No assignments yet. Add tasks first.")
    else:
        total_tasks = len(df)
        total_hours = round(df["Hours"].sum(), 1)
        average_difficulty = round(df["Difficulty"].mean(), 2)
        completed_tasks = int(df["Completed"].sum())
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)
        high_risk = len(df[df["Risk Level"] == "High"])

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Tasks", total_tasks)
        col2.metric("Total Hours", total_hours)
        col3.metric("Avg Difficulty", average_difficulty)
        col4.metric("Completion Rate", f"{completion_rate}%")
        col5.metric("High Risk", high_risk)

        st.subheader("Priority Table")
        st.dataframe(
            df.sort_values("Priority Score", ascending=False)[
                [
                    "Assignment",
                    "Subject",
                    "Hours",
                    "Difficulty",
                    "Days Left",
                    "Priority Score",
                    "Risk Level",
                    "Status"
                ]
            ],
            use_container_width=True
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Hours by Subject")
            st.bar_chart(df.groupby("Subject")["Hours"].sum())

        with col_b:
            st.subheader("Average Difficulty")
            st.bar_chart(df.groupby("Subject")["Difficulty"].mean())

        st.subheader("Risk Score by Assignment")
        st.bar_chart(df.set_index("Assignment")["Priority Score"])

        top_task = df.sort_values("Priority Score", ascending=False).iloc[0]
        hardest_subject = df.groupby("Subject")["Difficulty"].mean().idxmax()
        most_time_subject = df.groupby("Subject")["Hours"].sum().idxmax()

        st.subheader("Study Recommendation")
        st.write(f"Most urgent task: **{top_task['Assignment']}**")
        st.write(f"Hardest subject: **{hardest_subject}**")
        st.write(f"Most time-consuming subject: **{most_time_subject}**")

        if top_task["Days Left"] <= 1:
            st.warning("You have a task due very soon. Finish it first.")
        elif completion_rate < 50:
            st.warning("Your completion rate is low. Start with smaller tasks.")
        else:
            st.success("Your workload looks under control.")


# =====================
# AI ADVISOR
# =====================

elif page == "AI Advisor":
    st.header("🤖 AI Study Advisor V4")

    st.write("This page supports both rule-based advice and optional real OpenAI API advice.")

    df = assignment_dataframe(st.session_state.user)

    workload = st.text_area("Describe your current workload or stress level")

    use_real_ai = st.checkbox(
        "Use real OpenAI API if configured in Streamlit secrets"
    )

    if st.button("Generate Smart Study Plan"):
        if use_real_ai:
            try:
                ai_advice = generate_openai_advice(df, workload)
                if ai_advice:
                    st.subheader("Real AI Study Plan")
                    st.write(ai_advice)
                else:
                    st.warning("OpenAI API is not configured. Showing rule-based plan instead.")
                    st.text(generate_rule_based_advice(df, workload))
            except Exception as e:
                st.warning("Real AI failed. Showing rule-based plan instead.")
                st.text(generate_rule_based_advice(df, workload))
        else:
            st.subheader("Rule-Based Smart Study Plan")
            st.text(generate_rule_based_advice(df, workload))

    with st.expander("How to enable real AI"):
        st.write("""
Create a file called `.streamlit/secrets.toml` in your project folder.

Add:

OPENAI_API_KEY = "your_api_key_here"

Then install:

pip3 install openai

Restart the app.
""")


# =====================
# AP COUNTDOWN
# =====================

elif page == "AP Countdown":
    st.header("📅 AP Exam Countdown V4")

    with st.form("exam_form"):
        exam_name = st.text_input("Exam Name")
        subject = st.text_input("Subject")
        exam_date = st.date_input("Exam Date", min_value=date.today())
        add_exam = st.form_submit_button("Add Exam")

    if add_exam:
        if exam_name and subject:
            cursor.execute("""
            INSERT INTO exams(username, exam_name, subject, exam_date)
            VALUES(?,?,?,?)
            """, (
                st.session_state.user,
                exam_name,
                subject,
                str(exam_date)
            ))
            conn.commit()
            st.success("Exam added.")
        else:
            st.warning("Please enter exam name and subject.")

    cursor.execute("""
    SELECT id, exam_name, subject, exam_date
    FROM exams
    WHERE username=?
    ORDER BY exam_date
    """, (st.session_state.user,))

    exams = cursor.fetchall()

    if exams:
        today = date.today()

        for exam in exams:
            exam_id, name, subject, exam_date_text = exam
            d = datetime.strptime(exam_date_text, "%Y-%m-%d").date()
            days_left = (d - today).days

            st.metric(f"{name} ({subject})", f"{days_left} days left")

            if st.button(f"Delete {name}", key=f"delete_exam_{exam_id}"):
                cursor.execute(
                    "DELETE FROM exams WHERE id=? AND username=?",
                    (exam_id, st.session_state.user)
                )
                conn.commit()
                st.rerun()
    else:
        st.info("No exams added yet.")


# =====================
# STUDY TRACKER
# =====================

elif page == "Study Tracker":
    st.header("⏱️ Study Time Tracker V4")

    with st.form("study_log_form"):
        subject = st.text_input("Subject")
        minutes = st.number_input("Minutes Studied", 5, 600, 45, step=5)
        log_date = st.date_input("Study Date", value=date.today())
        notes = st.text_area("Notes")
        add_log = st.form_submit_button("Add Study Log")

    if add_log:
        if subject:
            cursor.execute("""
            INSERT INTO study_logs(username, subject, minutes, log_date, notes)
            VALUES(?,?,?,?,?)
            """, (
                st.session_state.user,
                subject,
                minutes,
                str(log_date),
                notes
            ))
            conn.commit()
            st.success("Study log added.")
        else:
            st.warning("Please enter a subject.")

    cursor.execute("""
    SELECT subject, minutes, log_date, notes
    FROM study_logs
    WHERE username=?
    ORDER BY log_date DESC
    """, (st.session_state.user,))

    logs = cursor.fetchall()

    if logs:
        log_df = pd.DataFrame(
            logs,
            columns=["Subject", "Minutes", "Date", "Notes"]
        )

        log_df["Date"] = pd.to_datetime(log_df["Date"])
        total_minutes = int(log_df["Minutes"].sum())
        total_hours = round(total_minutes / 60, 2)

        st.metric("Total Study Hours Logged", total_hours)

        st.subheader("Study Time by Subject")
        st.bar_chart(log_df.groupby("Subject")["Minutes"].sum() / 60)

        st.subheader("Recent Study Logs")
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No study logs yet.")


# =====================
# WEEKLY REPORT PDF
# =====================

elif page == "Weekly Report PDF":
    st.header("📄 Weekly Report PDF V4")

    st.write("Download a professional weekly report for your engineering project documentation.")

    pdf_buffer = create_pdf_report(st.session_state.user)

    filename = "StudyPilot_Weekly_Report.pdf" if REPORTLAB_AVAILABLE else "StudyPilot_Weekly_Report.txt"
    mime = "application/pdf" if REPORTLAB_AVAILABLE else "text/plain"

    st.download_button(
        label="Download Report",
        data=pdf_buffer,
        file_name=filename,
        mime=mime
    )

    st.subheader("Text Preview")
    st.text(create_text_report(st.session_state.user))


# =====================
# USER TESTING SURVEY
# =====================

elif page == "User Testing Survey":
    st.header("🧪 User Testing Survey V4")

    st.write("Use this page when classmates test your app. Their feedback becomes project evidence.")

    with st.form("survey_form"):
        student_name = st.text_input("Tester Name")
        grade_level = st.selectbox("Grade Level", ["9", "10", "11", "12", "Other"])
        ease = st.slider("How easy was the app to use?", 1, 5, 4)
        usefulness = st.slider("How useful was the app?", 1, 5, 4)
        recommend = st.slider("How likely are you to recommend it?", 1, 5, 4)
        feedback = st.text_area("Feedback or suggestions")
        submit_survey = st.form_submit_button("Submit Feedback")

    if submit_survey:
        cursor.execute("""
        INSERT INTO survey_results(
            username,
            student_name,
            grade_level,
            ease_of_use,
            usefulness,
            would_recommend,
            feedback,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?)
        """, (
            st.session_state.user,
            student_name,
            grade_level,
            ease,
            usefulness,
            recommend,
            feedback,
            str(datetime.now())
        ))
        conn.commit()
        st.success("Feedback saved.")

    cursor.execute("""
    SELECT student_name, grade_level, ease_of_use, usefulness, would_recommend, feedback, created_at
    FROM survey_results
    WHERE username=?
    ORDER BY created_at DESC
    """, (st.session_state.user,))

    results = cursor.fetchall()

    if results:
        survey_df = pd.DataFrame(
            results,
            columns=[
                "Tester",
                "Grade",
                "Ease",
                "Usefulness",
                "Recommend",
                "Feedback",
                "Date"
            ]
        )

        st.subheader("Survey Results")
        st.dataframe(survey_df, use_container_width=True)

        st.metric("Average Usefulness", round(survey_df["Usefulness"].mean(), 2))
        st.metric("Average Recommendation Score", round(survey_df["Recommend"].mean(), 2))
    else:
        st.info("No survey results yet.")


# =====================
# PROJECT INFO
# =====================

elif page == "Project Info":
    st.header("🚀 Project Info")

    st.write("""
StudyPilot AI V4 is a student productivity platform built with Python, Streamlit, SQLite, data analytics, PDF generation, and optional OpenAI API integration.

Core Features:
- User login and registration
- Homework planner
- Priority scoring algorithm
- Grade recovery calculator
- Study analytics dashboard
- AI-like and optional real AI study advisor
- AP exam countdown
- Study time tracker
- PDF weekly report export
- User testing survey system
""")

    st.subheader("College Application Description")

    st.write("""
Founder & Lead Developer, StudyPilot AI

Designed and developed a Python-based academic planning platform that helps students manage assignments, prioritize workloads, predict grade recovery goals, track study habits, and generate personalized study recommendations. Built the project using Streamlit, SQLite, data analytics, PDF reporting, and optional AI API integration to solve real student time-management problems. Conducted user testing with classmates and used feedback to improve usability and functionality.
""")

    st.subheader("Research + Testing Plan")

    st.write("""
1. Survey 50-100 students about homework stress, procrastination, and grade recovery needs.
2. Ask 20-50 classmates to test StudyPilot AI.
3. Collect feedback using the built-in User Testing Survey.
4. Compare before/after results:
   - missing assignments
   - late work
   - study hours
   - perceived organization
5. Add results to GitHub README and college application portfolio.
""")

    st.subheader("Deployment Plan")

    st.write("""
1. Push code to GitHub.
2. Create requirements.txt.
3. Deploy with Streamlit Cloud.
4. Add screenshots and demo video to README.
5. Share the link with classmates for testing.
""")
