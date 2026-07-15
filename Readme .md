# CourseCompass — Course Recommendation App

A full-stack course recommendation web app with AI advisor powered by Claude.

## Files
```
app.py       ← Python Flask backend (API + Claude AI)
index.html   ← Frontend (HTML + CSS + JS — single file)
```

## Quick Start

### 1. Install dependencies
```bash
pip install flask flask-cors anthropic
```

### 2. Set your Anthropic API key
```bash
# Mac / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run the server
```bash
python app.py
```

### 4. Open the app
Visit http://localhost:5000 in your browser.

---

## Features

**Browse View**
- Search by title, skill, platform keyword
- Filter by: Category, Level (Beginner/Intermediate/Advanced), Free/Paid
- Sort by: Rating, Duration, Price, Title
- Range sliders for max hours and min rating
- Direct "Enroll" link to the real course platform

**AI Advisor (Claude-powered)**
- Chat with Claude to describe your goals
- Claude picks 3–6 best-matching courses from the 33-course database
- Returns reasoning for each recommendation
- Remembers conversation history (last 6 turns)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses` | List/filter/sort courses |
| GET | `/api/categories` | All categories |
| GET | `/api/course/<id>` | Single course detail |
| POST | `/api/recommend` | AI course recommendation |

### Query params for `/api/courses`
- `q` — keyword search
- `category` — e.g. `AI / ML`
- `level` — `Beginner`, `Intermediate`, `Advanced`
- `price` — `free` or `paid`
- `min_rating` — float (e.g. `4.5`)
- `max_hours` — int
- `sort` — `rating`, `hours_asc`, `hours_desc`, `price_asc`, `title`

### POST `/api/recommend` body
```json
{
  "message": "I want to learn Python for data science in 3 months",
  "history": []
}
```

---

## Extend the Course Database

Add entries to the `COURSES` list in `app.py`:
```python
{
  "id": 34,
  "title": "Your Course Title",
  "platform": "Platform Name",
  "category": "Programming",  # or any existing category
  "level": "Beginner",        # Beginner | Intermediate | Advanced
  "rating": 4.7,
  "hours": 25,
  "price": 0,                 # 0 = free, else USD price
  "skills": ["Skill1","Skill2"],
  "url": "https://course-url.com"
}
``` 