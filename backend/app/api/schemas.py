from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    paper_ids: list[str] | None = None

class CompareRequest(BaseModel):
    paper_ids: list[str] = Field(min_length=2)

class GapRequest(BaseModel):
    paper_ids: list[str] | None = None
