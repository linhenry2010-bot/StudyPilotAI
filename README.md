# StudyPilot AI V4

StudyPilot AI is an academic planning platform for high school students.

## Features

- Login and registration
- Homework planner
- Priority score algorithm
- Grade recovery calculator
- Study analytics dashboard
- AI-like study advisor
- Optional OpenAI API integration
- AP countdown
- Study time tracker
- PDF weekly report
- User testing survey system

## How to Run

```bash
pip3 install -r requirements.txt
python3 -m streamlit run app.py
```

## Optional Real AI Setup

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
OPENAI_API_KEY = "your_api_key_here"
```

## College Application Description

Designed and developed a Python-based academic planning platform that helps students manage assignments, prioritize workloads, predict grade recovery goals, track study habits, and generate personalized study recommendations. Built the project using Streamlit, SQLite, data analytics, PDF reporting, and optional AI API integration to solve real student time-management problems.

## User Testing Plan

1. Survey 50-100 students.
2. Ask 20-50 students to test the app.
3. Collect feedback using the built-in survey.
4. Analyze usefulness, ease of use, and recommendation scores.
5. Add screenshots and results to this README.
