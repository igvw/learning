from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


type QuestionType = Literal["single_text", "multi_text", "ordered_multi", "inline_cloze", "computed_text"]
type PriorityMode = Literal["high", "mid", "low"]
type ScheduleBucket = Literal[
    "hot0",
    "hot1",
    "hot1_sit_out",
    "due_review",
    "cooling",
    "bucket_retry_wait",
    "unseen",
    "mastery",
]
type LogicalBucket = Literal["review", "unseen", "1h", "3h", "6h", "12h", "1d", "3d", "7d", "14d", "mastery"]

class ModuleNodeOut(BaseModel):
    id: int
    title: str
    slug: str
    full_slug: str
    instruction: str = ""
    children: list["ModuleNodeOut"] = Field(default_factory=list)


class CreateModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None
    instruction: str = ""


class UserCreateIn(BaseModel):
    handle: str = Field(min_length=1, max_length=60)
    display_name: str = Field(min_length=1, max_length=120)


class UserOut(BaseModel):
    id: int
    handle: str
    display_name: str
    created_at: str


class HealthOut(BaseModel):
    status: str
    instance_key: str


class QuizSessionCreateIn(BaseModel):
    module_id: int | None = None
    count: int = Field(default=10, ge=1, le=50)


class QuizItemOut(BaseModel):
    id: int
    position: int
    question_id: int
    module_id: int
    module_instruction: str = ""
    review_flag: bool
    prompt: str
    question_type: QuestionType
    rank: int
    type_config: dict[str, Any]
    submitted_answer: list[str] | None = None
    is_correct: bool | None = None
    score_earned: float | None = None
    score_possible: float = 1.0


class QuizSessionOut(BaseModel):
    id: int
    module_id: int | None = None
    completed_at: str | None = None
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
    rank: int = Field(default=1, ge=1)
    priority_mode: PriorityMode | None = None
    accepted_answers: list[list[str]] = Field(min_length=1)
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

        if self.question_type in {"single_text", "computed_text"}:
            if len(self.accepted_answers) != 1:
                raise ValueError(f"{self.question_type} questions expect exactly one answer group.")
            if self.segments:
                raise ValueError(f"{self.question_type} questions do not use segments.")
        elif self.question_type in {"multi_text", "ordered_multi"}:
            if self.segments:
                raise ValueError("multi-text questions do not use inline segments.")
        elif self.question_type == "inline_cloze":
            if len(self.segments) != len(self.accepted_answers) + 1:
                raise ValueError("inline_cloze questions require exactly one more segment than answer groups.")
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


class QuestionScheduleOut(BaseModel):
    bucket: ScheduleBucket
    logical_bucket: LogicalBucket
    recovery_streak: int | None = None
    interval_step: int | None = None
    last_incorrect_at: str | None = None
    next_due_at: str | None = None
    retry_pending: bool = False


class QuestionRowOut(BaseModel):
    question_id: int
    module_id: int
    module_full_slug: str
    prompt: str
    prompt_preview: str
    question_type: QuestionType
    rank: int
    attempts: int
    correct_percentage: float
    last_asked_at: str | None = None
    review_flag: bool
    accepted_answers: list[list[str]]
    segments: list[str]
    recent_incorrect_answers: list[dict[str, Any]] = Field(default_factory=list)
    schedule: QuestionScheduleOut


class StatsResponseOut(BaseModel):
    summary: StatsSummaryOut
    recent_sessions: list[RecentSessionOut]
    questions: list[QuestionRowOut]


class QuestionImportRowIn(BaseModel):
    row_number: int = Field(ge=1)
    qml_line: str


class ValidateQuestionImportIn(BaseModel):
    module_id: int
    qml_text: str | None = None
    rows: list[QuestionImportRowIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> "ValidateQuestionImportIn":
        has_qml_text = bool(self.qml_text and self.qml_text.strip())
        has_rows = bool(self.rows)
        if has_qml_text == has_rows:
            raise ValueError("Provide either qml_text or rows.")
        return self


class CommitQuestionImportIn(BaseModel):
    module_id: int
    rows: list[QuestionImportRowIn] = Field(default_factory=list, min_length=1)


class QuestionImportUnresolvedRowOut(BaseModel):
    row_number: int
    qml_line: str
    issues: list[str]
    inferred_type: QuestionType | None = None


class QuestionImportSkippedRowOut(BaseModel):
    row_number: int
    qml_line: str
    reason: str
    inferred_type: QuestionType | None = None


class QuestionImportResultOut(BaseModel):
    ready_to_commit: bool
    valid_row_count: int
    skipped_duplicate_count: int
    skipped_rows: list[QuestionImportSkippedRowOut] = Field(default_factory=list)
    unresolved_rows: list[QuestionImportUnresolvedRowOut]
    report_text: str
    committed: bool = False
    committed_count: int = 0
