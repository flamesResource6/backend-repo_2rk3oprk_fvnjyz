import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents

app = FastAPI(title="Study App API", version="1.1.0")

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

class TopicOut(BaseModel):
    id: str
    chapter_id: str
    title: str
    content: Optional[str] = None

class NoteIn(BaseModel):
    title: str
    body: str

class NoteOut(NoteIn):
    id: str
    chapter_id: str

class MCQOut(BaseModel):
    id: str
    chapter_id: str
    question: str
    options: List[str]
    answer_index: int = Field(..., ge=0)

class MCQAnswerIn(BaseModel):
    answer_index: int = Field(..., ge=0)

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

SEED_TOPICS = {
    ("Economics", 1): [
        {"title": "Definitions of Economics", "content": "Wealth, Welfare, Scarcity, Growth definitions."},
        {"title": "Micro vs Macro", "content": "Scope and limitations of micro economics."},
    ],
    ("Book Keeping & Accountancy", 1): [
        {"title": "Final Accounts Components", "content": "Trading, P&L Account and Balance Sheet."},
    ],
}

SEED_MCQS = {
    ("Economics", 1): [
        {
            "question": "Microeconomics studies _____.",
            "options": ["Aggregate demand", "Individual units", "National income", "General price level"],
            "answer_index": 1,
        },
        {
            "question": "Utility is the _____ derived from a commodity.",
            "options": ["cost", "satisfaction", "production", "income"],
            "answer_index": 1,
        },
    ],
    ("Book Keeping & Accountancy", 1): [
        {
            "question": "Which is prepared to ascertain gross profit?",
            "options": ["Trading Account", "Balance Sheet", "P&L Appropriation A/c", "Trial Balance"],
            "answer_index": 0,
        }
    ],
}

# ---------- Helpers ----------

def _id_str(doc):
    return str(doc.get("_id"))

async def ensure_seed(board: str, standard: str):
    """Ensure seed subjects and chapters exist in DB for given board/standard."""
    try:
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
        # Seed some topics and mcqs for sample chapters
        for (subj_name, number), topics in SEED_TOPICS.items():
            sid = id_map.get(subj_name)
            if not sid:
                continue
            chs = get_documents("chapter", {"subject_id": sid, "number": number})
            if chs:
                ch_id = _id_str(chs[0])
                if not get_documents("topic", {"chapter_id": ch_id}):
                    for t in topics:
                        create_document("topic", {**t, "chapter_id": ch_id})
        for (subj_name, number), mcqs in SEED_MCQS.items():
            sid = id_map.get(subj_name)
            if not sid:
                continue
            chs = get_documents("chapter", {"subject_id": sid, "number": number})
            if chs:
                ch_id = _id_str(chs[0])
                if not get_documents("mcq", {"chapter_id": ch_id}):
                    for m in mcqs:
                        create_document("mcq", {**m, "chapter_id": ch_id})
    except Exception:
        # Database might not be configured; ignore to allow API to still work
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
    fallback = [s for s in SEED_SUBJECTS if s["board"] == board and s["standard"] == standard]
    return [SubjectOut(id=str(i), **s) for i, s in enumerate(fallback, start=1)]

@app.get("/api/subjects/{subject_id}/chapters", response_model=List[ChapterOut])
async def list_chapters(subject_id: str):
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
        # Map via seed if subject_id is ObjectId-like but not matching
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

# ------- Topics -------
@app.get("/api/chapters/{chapter_id}/topics", response_model=List[TopicOut])
async def list_topics(chapter_id: str):
    # Try DB
    try:
        docs = get_documents("topic", {"chapter_id": chapter_id})
        if docs:
            return [TopicOut(id=_id_str(d), chapter_id=d.get("chapter_id"), title=d.get("title"), content=d.get("content")) for d in docs]
        # Fallback via seed: chapter_id pattern "<subjectid>-<number>"
        subj_id, number = chapter_id.split("-", 1)
        number = int(number)
        subs = get_documents("subject", {})
        sub_by_id = { _id_str(s): s.get("name") for s in subs }
        subj_name = sub_by_id.get(subj_id)
        if subj_name:
            items = SEED_TOPICS.get((subj_name, number), [])
            return [TopicOut(id=f"{chapter_id}-t{i}", chapter_id=chapter_id, title=t["title"], content=t.get("content")) for i, t in enumerate(items, start=1)]
    except Exception:
        pass
    # Pure seed fallback based on enumeration: subject order -> chapter number
    try:
        sid, number = chapter_id.split("-", 1)
        idx = int(sid) - 1
        number = int(number)
        name = [s for s in SEED_SUBJECTS if s["board"] == "Maharashtra" and s["standard"] == "12"][idx]["name"]
        items = SEED_TOPICS.get((name, number), [])
        return [TopicOut(id=f"{chapter_id}-t{i}", chapter_id=chapter_id, title=t["title"], content=t.get("content")) for i, t in enumerate(items, start=1)]
    except Exception:
        return []

# ------- Notes -------
@app.get("/api/chapters/{chapter_id}/notes", response_model=List[NoteOut])
async def list_notes(chapter_id: str):
    try:
        docs = get_documents("note", {"chapter_id": chapter_id})
        return [NoteOut(id=_id_str(d), chapter_id=d.get("chapter_id"), title=d.get("title"), body=d.get("body")) for d in docs]
    except Exception:
        # DB required for notes; without DB there are no personal notes
        return []

@app.post("/api/chapters/{chapter_id}/notes", response_model=NoteOut)
async def create_note(chapter_id: str, payload: NoteIn):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured. Notes require database.")
    note_id = create_document("note", {"chapter_id": chapter_id, **payload.model_dump()})
    return NoteOut(id=note_id, chapter_id=chapter_id, **payload.model_dump())

# ------- MCQs -------
@app.get("/api/chapters/{chapter_id}/mcqs", response_model=List[MCQOut])
async def list_mcqs(chapter_id: str):
    try:
        docs = get_documents("mcq", {"chapter_id": chapter_id})
        if docs:
            return [MCQOut(id=_id_str(d), chapter_id=d.get("chapter_id"), question=d.get("question"), options=d.get("options", []), answer_index=d.get("answer_index", 0)) for d in docs]
        # Fallback using seed
        subj_part, number = chapter_id.split("-", 1)
        number = int(number)
        subs = get_documents("subject", {})
        sub_by_id = { _id_str(s): s.get("name") for s in subs }
        subj_name = sub_by_id.get(subj_part)
        if subj_name:
            items = SEED_MCQS.get((subj_name, number), [])
            return [MCQOut(id=f"{chapter_id}-q{i}", chapter_id=chapter_id, question=m["question"], options=m.get("options", []), answer_index=m.get("answer_index", 0)) for i, m in enumerate(items, start=1)]
    except Exception:
        pass
    # Pure fallback based on subject enumeration index in seed
    try:
        sid, number = chapter_id.split("-", 1)
        idx = int(sid) - 1
        number = int(number)
        name = [s for s in SEED_SUBJECTS if s["board"] == "Maharashtra" and s["standard"] == "12"][idx]["name"]
        items = SEED_MCQS.get((name, number), [])
        return [MCQOut(id=f"{chapter_id}-q{i}", chapter_id=chapter_id, question=m["question"], options=m.get("options", []), answer_index=m.get("answer_index", 0)) for i, m in enumerate(items, start=1)]
    except Exception:
        return []

@app.post("/api/chapters/{chapter_id}/mcqs", response_model=MCQOut)
async def create_mcq(chapter_id: str, payload: MCQOut):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured. Creating MCQs requires database.")
    data = payload.model_dump()
    data.pop("id", None)
    data["chapter_id"] = chapter_id
    mcq_id = create_document("mcq", data)
    return MCQOut(id=mcq_id, **data)

@app.post("/api/chapters/{chapter_id}/mcqs/{mcq_id}/check")
async def check_mcq_answer(chapter_id: str, mcq_id: str, answer: MCQAnswerIn = Body(...)):
    # If DB exists, try to fetch; otherwise, infer from id format in seed
    try:
        docs = get_documents("mcq", {"_id": mcq_id})
        if docs:
            correct = int(docs[0].get("answer_index", 0))
            return {"correct": answer.answer_index == correct}
    except Exception:
        pass
    # Seed id format: <chapter_id>-qN
    if mcq_id.startswith(f"{chapter_id}-q"):
        try:
            n = int(mcq_id.split("-q")[-1]) - 1
            # Map to seed
            try:
                subj_part, number = chapter_id.split("-", 1)
                idx = int(subj_part) - 1
                number = int(number)
                subj_name = [s for s in SEED_SUBJECTS if s["board"] == "Maharashtra" and s["standard"] == "12"][idx]["name"]
                correct = SEED_MCQS[(subj_name, number)][n]["answer_index"]
            except Exception:
                # try resolve via subjects collection
                try:
                    subs = get_documents("subject", {})
                    sub_by_id = { _id_str(s): s.get("name") for s in subs }
                    subj_name = sub_by_id.get(subj_part)
                    correct = SEED_MCQS[(subj_name, int(number))][n]["answer_index"]
                except Exception:
                    return {"correct": False}
            return {"correct": answer.answer_index == correct}
        except Exception:
            return {"correct": False}
    return {"correct": False}

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
