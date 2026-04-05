from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


QuestionType = Literal["single_text", "multi_text", "ordered_multi", "inline_cloze"]


class ModuleUiCopy(BaseModel):
    question_label: str = "Question"
    answer_label: str = "Answer"
    stats_title: str = "Stats"
    review_title: str = "Review"


class ModuleNodeOut(BaseModel):
    id: int
    source_id: Optional[str] = None
    title: str
    slug: str
    full_slug: str
    ui_copy: ModuleUiCopy
    children: list["ModuleNodeOut"] = Field(default_factory=list)


class CreateModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    parent_id: Optional[int] = None
    ui_copy: ModuleUiCopy = Field(default_factory=ModuleUiCopy)


class QuizSessionCreateIn(BaseModel):
    module_id: Optional[int] = None
    count: int = Field(default=10, ge=1, le=50)


class QuizItemOut(BaseModel):
    id: int
    position: int
    question_id: int
    review_flag: bool
    prompt: str
    question_type: QuestionType
    ranking: float
    type_config: dict[str, Any]
    submitted_answer: Optional[List[str]] = None
    is_correct: Optional[bool] = None
    score_earned: Optional[float] = None
    score_possible: float = 1.0


class QuizSessionOut(BaseModel):
    id: int
    module_id: Optional[int] = None
    completed_at: Optional[str] = None
    items: list[QuizItemOut]


class SlotResultOut(BaseModel):
    index: int
    is_correct: bool
    expected: str


class SubmitAnswerIn(BaseModel):
    answers: list[str] = Field(default_factory=list)


class SubmitAnswerOut(BaseModel):
    item_id: int
    is_correct: bool
    score_earned: float
    score_possible: float
    slot_results: list[SlotResultOut]
    canonical_answers: list[str]
    session_completed: bool
    submitted_answer: list[str]


class QuestionDraftIn(BaseModel):
    module_id: int
    prompt: str = Field(min_length=1)
    question_type: QuestionType
    ranking: float = Field(default=1, ge=0)
    review_flag: bool = False
    accepted_answers: list[list[str]] = Field(min_length=1)
    slot_prompts: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "QuestionDraftIn":
        cleaned_groups = []
        for group in self.accepted_answers:
            cleaned = [value.strip() for value in group if value and value.strip()]
            if not cleaned:
                raise ValueError("Each answer group needs at least one accepted answer.")
            cleaned_groups.append(cleaned)
        self.accepted_answers = cleaned_groups

        if self.question_type == "single_text":
            if len(self.accepted_answers) != 1:
                raise ValueError("single_text questions expect exactly one answer group.")
            if self.slot_prompts or self.segments:
                raise ValueError("single_text questions do not use slot prompts or segments.")
        elif self.question_type in {"multi_text", "ordered_multi"}:
            if self.slot_prompts and len(self.slot_prompts) != len(self.accepted_answers):
                raise ValueError("multi-text slot prompts must match answer group count when provided.")
            if self.segments:
                raise ValueError("multi-text questions do not use inline segments.")
        elif self.question_type == "inline_cloze":
            if len(self.segments) != len(self.accepted_answers) + 1:
                raise ValueError("inline_cloze questions require exactly one more segment than answer groups.")
            if self.slot_prompts:
                raise ValueError("inline_cloze questions do not use slot prompts.")
        return self


class QuestionRevisionIn(QuestionDraftIn):
    reset_stats: bool = True


class QuestionMutationOut(BaseModel):
    question_id: int


class QuestionReviewFlagIn(BaseModel):
    review_flag: bool


class QuestionReviewFlagOut(BaseModel):
    question_id: int
    review_flag: bool


class RecentSessionOut(BaseModel):
    session_id: int
    created_at: str
    answered_count: int
    correct_count: float
    score_possible: float
    accuracy: float


class StatsSummaryOut(BaseModel):
    total_questions: int
    reviewed_questions: int
    total_attempts: int
    total_correct: float
    total_possible: float
    accuracy: float


class QuestionRowOut(BaseModel):
    question_id: int
    module_id: int
    module_title: str
    prompt: str
    prompt_preview: str
    question_type: QuestionType
    ranking: float
    attempts: int
    correct_percentage: float
    last_asked_at: Optional[str] = None
    review_flag: bool
    accepted_answers: list[list[str]]
    slot_prompts: list[str]
    segments: list[str]


class StatsResponseOut(BaseModel):
    summary: StatsSummaryOut
    recent_sessions: list[RecentSessionOut]
    questions: list[QuestionRowOut]
