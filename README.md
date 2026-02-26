# AI Travel Itinerary Planner

A full-stack web app that generates personalized, day-by-day travel itineraries using an LLM. Built with **FastAPI** (Python) on the backend and a single-page HTML/CSS/JS frontend.

---

## Features

- **AI-generated itineraries** — hotel, breakfast, lunch, dinner, and sightseeing spots for every day of the trip
- **Personalized recommendations** — optional free-text preferences field (e.g. "I love ramen", "vegetarian only", "must visit teamLab")
- **Google Maps links** — every place comes with a direct Maps search link
- **Budget-aware** — LLM keeps the total cost within the provided budget and shows per-day cost breakdown
- **Input validation** — 14-day max trip, $50–$500,000 budget range, start date ≥ today, end date ≥ start date (enforced on both frontend and backend)
- **Provider-flexible** — works with OpenAI, GitHub Models (free), or any OpenAI-compatible endpoint

---

## Project Structure

```
.
├── app/
│   ├── main.py               # FastAPI app, CORS, static file serving
│   ├── models.py             # Pydantic request/response models
│   ├── routers/
│   │   └── itinerary.py      # POST /itinerary/ endpoint
│   └── services/
│       └── llm_service.py    # OpenAI client, prompt building, response parsing
├── frontend/
│   └── index.html            # Single-page UI (HTML + CSS + JS)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Quick Start

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd test-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Option A — OpenAI**
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Option B — GitHub Models (free)**

Generate a [fine-grained GitHub PAT](https://github.com/settings/tokens) (no special scopes required for public models).

```env
OPENAI_API_KEY=github_pat_...
OPENAI_BASE_URL=https://models.inference.ai.azure.com
OPENAI_MODEL=gpt-4o-mini
```

### 4. Launch the app

Make sure your virtual environment is activated, then start the server:

**Windows (PowerShell)**
```powershell
.venv\Scripts\activate
uvicorn app.main:app --reload
```

**macOS / Linux**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process using WatchFiles
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Open the app in your browser:**

👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

**Other useful URLs while the server is running:**

| URL | Description |
|---|---|
| `http://127.0.0.1:8000` | Main app (frontend UI) |
| `http://127.0.0.1:8000/docs` | Interactive API docs (Swagger UI) |
| `http://127.0.0.1:8000/redoc` | Alternative API docs (ReDoc) |

**To stop the server:** press `Ctrl + C` in the terminal.

> **Note:** The `--reload` flag auto-restarts the server whenever you edit a Python file. For production, omit it and use a process manager like `gunicorn` or `supervisor`.

---

### Using the App

1. Enter a **destination city** (e.g. `Tokyo`, `Paris`, `New York City`)
2. Pick a **start date** and **end date** (max 14 days, start must be today or later)
3. Enter your **total budget** in USD
4. Optionally add **preferences** (e.g. `"I love ramen and must visit teamLab"`, `"vegetarian meals"`, `"luxury hotels"`)
5. Click **Generate Itinerary** — the AI will take ~20–40 seconds to respond
6. Your day-by-day itinerary appears below the form with hotels, meals, sightseeing, prices, and Google Maps links

---

## API

### `POST /itinerary/`

Generate a travel itinerary.

**Request body**

| Field | Type | Required | Description |
|---|---|---|---|
| `city` | string | Yes | Destination city (e.g. `"Tokyo"`) |
| `start_date` | date | Yes | Trip start date (`YYYY-MM-DD`), must be today or future |
| `end_date` | date | Yes | Trip end date (`YYYY-MM-DD`), must be ≥ start date, max 14-day trip |
| `budget` | integer | Yes | Total budget in USD ($50–$500,000) |
| `preferences` | string | No | Free-text preferences, max 500 chars |

**Example**

```bash
curl -X POST http://127.0.0.1:8000/itinerary/ \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Tokyo",
    "start_date": "2026-03-01",
    "end_date": "2026-03-03",
    "budget": 800,
    "preferences": "I love ramen and want to visit teamLab Borderless"
  }'
```

**Response** — `ItineraryResponse` with `city`, `start_date`, `end_date`, `budget`, `estimated_total_price`, and an `itinerary` array of day objects, each containing `hotel`, `breakfast`, `lunch`, `dinner`, `sightseeing_spots`, and `est_daily_price`.

Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key or GitHub PAT |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name |
| `OPENAI_BASE_URL` | *(unset)* | Override base URL for GitHub Models or other compatible providers |

---

## Requirements

- Python 3.11+
- See `requirements.txt` for all package versions

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
openai>=1.30.0
python-dotenv>=1.0.0
pydantic>=2.7.0
aiofiles>=23.0.0
```
