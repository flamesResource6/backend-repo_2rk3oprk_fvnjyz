import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Study App API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Pydantic response models ---------
class SubjectOut(BaseModel):
    id: str
    board: str
    standard: str
    name: str
    stream: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

class ChapterOut(BaseModel):
    id: str
    subject_id: str
    number: int
    title: str
    summary: Optional[str] = None

# ---------- Seed Data (Maharashtra HSC 12th Commerce) ----------
SEED_SUBJECTS = [
    {
        "board": "Maharashtra",
        "standard": "12",
        "name": "Economics",
        "stream": "Commerce",
        "description": "Macro & micro economic concepts for HSC.",
        "icon": "📈",
    },
    {
        "board": "Maharashtra",
        "standard": "12",
        "name": "Book Keeping & Accountancy",
        "stream": "Commerce",
        "description": "Financial accounting and statements.",
        "icon": "📚",
    },
    {
        "board": "Maharashtra",
        "standard": "12",
        "name": "Secretarial Practice",
        "stream": "Commerce",
        "description": "Company secretary duties and documentation.",
        "icon": "📝",
    },
    {
        "board": "Maharashtra",
        "standard": "12",
        "name": "Organization of Commerce and Management",
        "stream": "Commerce",
        "description": "Business organization and management principles.",
        "icon": "🏢",
    },
]

SEED_CHAPTERS = {
    "Economics": [
        {"number": 1, "title": "Introduction to Micro Economics", "summary": "Basic concepts of micro economics."},
        {"number": 2, "title": "Utility Analysis", "summary": "Cardinal and ordinal utility."},
    ],
    "Book Keeping & Accountancy": [
        {"number": 1, "title": "Partnership Final Accounts", "summary": "Final accounts of partnership firm."},
        {"number": 2, "title": "Admission of Partner", "summary": "Revaluation, goodwill, capital adjustments."},
    ],
    "Secretarial Practice": [
        {"number": 1, "title": "Company Correspondence", "summary": "Notices, agenda, minutes."},
        {"number": 2, "title": "Share Capital", "summary": "Issue and allotment of shares."},
    ],
    "Organization of Commerce and Management": [
        {"number": 1, "title": "Principles of Management", "summary": "Planning, organizing, staffing, directing, controlling."},
        {"number": 2, "title": "Entrepreneurship Development", "summary": "Entrepreneurial characteristics and process."},
    ],
}

# ---------- Helpers ----------

def _id_str(doc):
    return str(doc.get("_id"))

async def ensure_seed(board: str, standard: str):
    """Ensure seed subjects and chapters exist in DB for given board/standard."""
    try:
        # Check if subjects exist
        existing = get_documents("subject", {"board": board, "standard": standard})
        names = {s.get("name") for s in existing}
        id_map = {s.get("name"): _id_str(s) for s in existing}

        for subj in SEED_SUBJECTS:
            if subj["board"] == board and subj["standard"] == standard and subj["name"] not in names:
                sid = create_document("subject", subj)
                id_map[subj["name"]] = sid
        # Seed chapters per subject if absent
        for subj_name, chapters in SEED_CHAPTERS.items():
            sid = id_map.get(subj_name)
            if not sid:
                continue
            existing_ch = get_documents("chapter", {"subject_id": sid})
            if not existing_ch:
                for ch in chapters:
                    create_document("chapter", {**ch, "subject_id": sid})
    except Exception:
        # Database might not be configured; ignore silently to allow API to still work
        pass

# ---------- Routes ----------
@app.get("/")
def root():
    return {"message": "Study App Backend Running"}

@app.get("/api/subjects", response_model=List[SubjectOut])
async def list_subjects(
    board: str = Query("Maharashtra"),
    standard: str = Query("12")
):
    # attempt to seed and then return from DB; fallback to seed constants
    await ensure_seed(board, standard)
    try:
        docs = get_documents("subject", {"board": board, "standard": standard})
        subjects = [
            SubjectOut(
                id=_id_str(d),
                board=d.get("board"),
                standard=d.get("standard"),
                name=d.get("name"),
                stream=d.get("stream"),
                description=d.get("description"),
                icon=d.get("icon"),
            )
            for d in docs
        ]
        if subjects:
            return subjects
    except Exception:
        pass
    # Fallback (no DB)
    fallback = [s for s in SEED_SUBJECTS if s["board"] == board and s["standard"] == standard]
    return [SubjectOut(id=str(i), **s) for i, s in enumerate(fallback, start=1)]

@app.get("/api/subjects/{subject_id}/chapters", response_model=List[ChapterOut])
async def list_chapters(subject_id: str):
    # Try DB first
    try:
        docs = get_documents("chapter", {"subject_id": subject_id})
        if docs:
            return [
                ChapterOut(
                    id=_id_str(d),
                    subject_id=d.get("subject_id"),
                    number=d.get("number"),
                    title=d.get("title"),
                    summary=d.get("summary"),
                )
                for d in docs
            ]
        # If subject_id is a fallback numeric string, map from seed
        # Find subject name via subjects collection
        subs = get_documents("subject", {})
        sub_by_id = { _id_str(s): s.get("name") for s in subs }
        name = sub_by_id.get(subject_id)
        if name and name in SEED_CHAPTERS:
            chapters = SEED_CHAPTERS[name]
            return [
                ChapterOut(
                    id=f"{subject_id}-{c['number']}",
                    subject_id=subject_id,
                    number=c["number"],
                    title=c["title"],
                    summary=c.get("summary"),
                )
                for c in chapters
            ]
    except Exception:
        pass
    # Pure fallback: subject_id likely from fallback enumeration index -> map name by order
    ordered = [s for s in SEED_SUBJECTS if s["board"] == "Maharashtra" and s["standard"] == "12"]
    try:
        idx = int(subject_id) - 1
        name = ordered[idx]["name"]
        chapters = SEED_CHAPTERS.get(name, [])
        return [
            ChapterOut(
                id=f"{subject_id}-{c['number']}",
                subject_id=subject_id,
                number=c["number"],
                title=c["title"],
                summary=c.get("summary"),
            )
            for c in chapters
        ]
    except Exception:
        raise HTTPException(status_code=404, detail="Chapters not found for subject")

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
