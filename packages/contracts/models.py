from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import CONTRACT_VERSION


class ChapterKind(str, Enum):
    NORMAL = "NORMAL"
    PROLOGUE = "PROLOGUE"
    SIDE_STORY = "SIDE_STORY"
    EXTRA = "EXTRA"


class ChapterStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class MergeStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PENDING_REVIEW = "PENDING_REVIEW"
    SPLIT_REQUIRED = "SPLIT_REQUIRED"


class MemoryGateAction(str, Enum):
    REVIEW_MANUALLY = "REVIEW_MANUALLY"
    AUTO_MERGE = "AUTO_MERGE"


class OutlineContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default=CONTRACT_VERSION)
    chapter_goal: str
    conflict: str
    beats: List[str]
    foreshadowing: List[str]
    ending_hook: str


class ReviewContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default=CONTRACT_VERSION)
    character_consistency_score: int = Field(ge=0, le=100)
    world_consistency_score: int = Field(ge=0, le=100)
    style_match_score: int = Field(ge=0, le=100)
    repetition_issues: List[str]
    revision_suggestions: List[str]

    @model_validator(mode="after")
    def ensure_requirement_checks_present(self) -> "ReviewContract":
        joined = "\n".join(self.revision_suggestions).lower()
        required = ["must_include", "must_not_include", "continuity_constraints"]
        missing = [item for item in required if item not in joined]
        if missing:
            raise ValueError(
                "revision_suggestions must explicitly include checks for: "
                + ", ".join(missing)
            )
        return self


class CharacterContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_id: str
    canonical_name: str
    display_name: str
    aliases: List[str]
    merge_status: MergeStatus = MergeStatus.CONFIRMED

    role: Optional[str] = ""
    age: Optional[int] = 0
    personality: List[str] = Field(default_factory=list)
    background: List[str] = Field(default_factory=list)
    abilities: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    relationships: Dict[str, Any] = Field(default_factory=dict)
    motivation: List[str] = Field(default_factory=list)
    key_memories: List[str] = Field(default_factory=list)
    story_function: List[str] = Field(default_factory=list)
    beliefs: List[str] = Field(default_factory=list)
    ambiguity: List[str] = Field(default_factory=list)
    identities: List[Dict[str, Any]] = Field(default_factory=list)


class CharactersContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default=CONTRACT_VERSION)
    characters: List[CharacterContract]


class ChapterMetaContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default=CONTRACT_VERSION)
    chapter_id: str
    kind: ChapterKind
    title: str
    subtitle: Optional[str] = None
    volume_id: Optional[str] = None
    arc_id: Optional[str] = None
    order_index: int
    status: ChapterStatus
    summary: str = ""
    created_at: datetime
    updated_at: datetime


class MemoryGateContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default=CONTRACT_VERSION)
    passed: bool = Field(alias="pass")
    issues: List[str]
    recommended_action: MemoryGateAction

