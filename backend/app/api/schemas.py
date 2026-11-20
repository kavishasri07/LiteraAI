from pydantic import BaseModel, ConfigDict, Field

class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ChatRequest(StrictRequest):
    question: str = Field(min_length=3, max_length=2000)
    paper_ids: list[str] | None = Field(default=None, max_length=50)

class CompareRequest(StrictRequest):
    paper_ids: list[str] = Field(min_length=2, max_length=50)

class GapRequest(StrictRequest):
    paper_ids: list[str] | None = Field(default=None, max_length=50)
