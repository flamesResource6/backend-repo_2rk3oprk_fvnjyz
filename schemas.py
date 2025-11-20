"""
Database Schemas for Study App

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class Subject(BaseModel):
    board: str = Field(..., description="Education board, e.g., Maharashtra")
    standard: str = Field(..., description="Class/grade e.g., 12")
    name: str = Field(..., description="Subject name")
    stream: Optional[str] = Field(None, description="Stream e.g., Science/Commerce/Arts")
    description: Optional[str] = Field(None, description="Short subject description")
    icon: Optional[str] = Field(None, description="Emoji or icon name")

class Chapter(BaseModel):
    subject_id: str = Field(..., description="Reference to subject _id as string")
    number: int = Field(..., ge=1, description="Chapter number")
    title: str = Field(..., description="Chapter title")
    summary: Optional[str] = Field(None, description="Short chapter overview")

class Topic(BaseModel):
    chapter_id: str = Field(..., description="Reference to chapter _id as string")
    title: str = Field(..., description="Topic title")
    content: Optional[str] = Field(None, description="Markdown or rich text content")
    resources: Optional[List[str]] = Field(default_factory=list, description="Useful links or references")

class Note(BaseModel):
    chapter_id: str = Field(..., description="Reference to chapter _id as string")
    title: str
    body: str

class MCQ(BaseModel):
    chapter_id: str = Field(..., description="Reference to chapter _id as string")
    question: str
    options: List[str]
    answer_index: int = Field(..., ge=0, description="Index of correct option")
