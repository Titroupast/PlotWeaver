from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from plotweaver_api.core.errors import NotFoundError, ValidationError
from plotweaver_api.db.models import ChapterVersion, Character, Memory, MemoryDelta, MergeDecision
from plotweaver_api.db.settings import settings
from plotweaver_api.repositories.character_repo import CharacterRepository
from plotweaver_api.repositories.memory_delta_repo import MemoryDeltaRepository
from plotweaver_api.repositories.memory_repo import MemoryRepository
from plotweaver_api.repositories.merge_decision_repo import MergeDecisionRepository
from plotweaver_api.schemas.memory import (
    CharacterResponse,
    MemoryDeltaDecisionRequest,
    MemoryDeltaDecisionResponse,
    MemoryDeltaResponse,
    MemoryHistoryItem,
    MemoryRebuildResponse,
    MemorySnapshotItem,
    MemorySnapshotResponse,
    MergeDecisionResponse,
)
from plotweaver_api.services.llm_prompts import render_prompt
from plotweaver_api.storage.interface import StorageClient


class MemoryService:
    _COMMON_SURNAMES = set(
        "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
        "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎连习容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东殴殳沃利蔚越夔隆师巩聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
    )
    def __init__(
        self,
        character_repo: CharacterRepository,
        memory_repo: MemoryRepository,
        delta_repo: MemoryDeltaRepository,
        decision_repo: MergeDecisionRepository,
        storage: StorageClient,
    ):
        self.character_repo = character_repo
        self.memory_repo = memory_repo
        self.delta_repo = delta_repo
        self.decision_repo = decision_repo
        self.storage = storage

    def list_characters(self, project_id: str, limit: int = 100, offset: int = 0) -> list[CharacterResponse]:
        return [self._to_character_response(row) for row in self.character_repo.list_by_project(project_id, limit, offset)]

    def list_memory_deltas(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[MemoryDeltaResponse]:
        if status:
            rows = self.delta_repo.list_by_project_status(project_id, status.upper(), limit, offset)
        else:
            rows = self.delta_repo.list_by_project(project_id, limit, offset)
        return [self._to_delta_response(row) for row in rows]

    def list_merge_decisions(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MergeDecisionResponse]:
        return [self._to_decision_response(row) for row in self.decision_repo.list_by_project(project_id, limit, offset)]

    def get_snapshots(self, project_id: str) -> MemorySnapshotResponse:
        rows = self.memory_repo.list_latest_by_project(project_id)
        return MemorySnapshotResponse(
            project_id=project_id,
            snapshots=[
                MemorySnapshotItem(
                    memory_type=row.memory_type,
                    version_no=row.version_no,
                    summary_json=row.summary_json,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
        )

    def list_history(self, project_id: str, limit: int = 100, offset: int = 0) -> list[MemoryHistoryItem]:
        rows = self.memory_repo.list_history(project_id, limit=limit, offset=offset)
        return [
            MemoryHistoryItem(
                id=str(row.id),
                memory_type=row.memory_type,
                version_no=row.version_no,
                summary_json=row.summary_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def rebuild_project_summary(self, project_id: str, user_id: str | None = None) -> MemoryRebuildResponse:
        chapter_corpus, chapter_count = self._build_project_chapter_corpus(project_id)
        if not chapter_corpus.strip():
            return MemoryRebuildResponse(
                project_id=project_id,
                updated_types=[],
                versions={},
                sources={},
                reasons={},
                chapter_count=chapter_count,
            )

        sources: dict[str, str] = {}
        reasons: dict[str, str] = {}
        try:
            characters, char_source, char_reason = self._summarize_characters(chapter_corpus, project_id)
            sources["CHARACTERS"] = char_source
            if char_reason:
                reasons["CHARACTERS"] = char_reason
        except Exception as exc:
            fallback = self._fallback_character_cards(project_id) or self._fallback_character_cards_from_corpus(chapter_corpus)
            characters = {"source": "FALLBACK", "characters": fallback}
            sources["CHARACTERS"] = "FALLBACK"
            reasons["CHARACTERS"] = f"EXCEPTION_IN_CHARACTER_SUMMARY: {exc}"
        try:
            world_rules, world_source, world_reason = self._summarize_world_rules(chapter_corpus)
            sources["WORLD_RULES"] = world_source
            if world_reason:
                reasons["WORLD_RULES"] = world_reason
        except Exception:
            world_rules = {"rules": self._fallback_world_rules(chapter_corpus)}
            sources["WORLD_RULES"] = "FALLBACK"
            reasons["WORLD_RULES"] = "EXCEPTION_IN_WORLD_RULE_SUMMARY"
        try:
            story, story_source, story_reason = self._summarize_story(chapter_corpus)
            sources["STORY_SO_FAR"] = story_source
            if story_reason:
                reasons["STORY_SO_FAR"] = story_reason
        except Exception:
            story = {"milestones": self._fallback_story(chapter_corpus)}
            sources["STORY_SO_FAR"] = "FALLBACK"
            reasons["STORY_SO_FAR"] = "EXCEPTION_IN_STORY_SUMMARY"

        updated_types: list[str] = []
        versions: dict[str, int] = {}

        changed, version = self._upsert_summary(project_id, "CHARACTERS", characters, user_id=user_id)
        if changed:
            updated_types.append("CHARACTERS")
        versions["CHARACTERS"] = version

        changed, version = self._upsert_summary(project_id, "WORLD_RULES", world_rules, user_id=user_id)
        if changed:
            updated_types.append("WORLD_RULES")
        versions["WORLD_RULES"] = version

        changed, version = self._upsert_summary(project_id, "STORY_SO_FAR", story, user_id=user_id)
        if changed:
            updated_types.append("STORY_SO_FAR")
        versions["STORY_SO_FAR"] = version

        self.memory_repo.session.flush()
        return MemoryRebuildResponse(
            project_id=project_id,
            updated_types=updated_types,
            versions=versions,
            sources=sources,
            reasons=reasons,
            chapter_count=chapter_count,
        )

    def decide_delta(
        self,
        project_id: str,
        delta_id: str,
        payload: MemoryDeltaDecisionRequest,
        user_id: str | None,
    ) -> MemoryDeltaDecisionResponse:
        delta = self.delta_repo.get(delta_id)
        if delta is None or delta.deleted_at is not None or str(delta.project_id) != project_id:
            raise NotFoundError("Memory delta not found", details={"project_id": project_id, "delta_id": delta_id})

        if delta.gate_status in {"MERGED", "REJECTED"}:
            recent = self.decision_repo.list_by_delta(delta_id, limit=1, offset=0)
            return MemoryDeltaDecisionResponse(
                delta=self._to_delta_response(delta),
                merge_decision=self._to_decision_response(recent[0]) if recent else None,
            )

        decision = payload.decision.upper()
        if decision not in {"MERGE", "REJECT"}:
            raise ValidationError("Unsupported memory decision", details={"decision": payload.decision})

        merge_decision = None
        now = datetime.now(timezone.utc)

        if decision == "MERGE":
            self._apply_delta_to_memory(delta)
            delta.gate_status = "MERGED"
            delta.applied_at = now
            delta.applied_by = user_id
            merge_decision = self.decision_repo.add(
                MergeDecision(
                    tenant_id=delta.tenant_id,
                    project_id=delta.project_id,
                    run_id=delta.run_id,
                    delta_id=delta.id,
                    decision_type="MERGE",
                    payload_json=delta.payload_json,
                    reason=payload.reason or "manual merge",
                    created_by=user_id,
                )
            )
        else:
            delta.gate_status = "REJECTED"
            delta.applied_at = now
            delta.applied_by = user_id
            merge_decision = self.decision_repo.add(
                MergeDecision(
                    tenant_id=delta.tenant_id,
                    project_id=delta.project_id,
                    run_id=delta.run_id,
                    delta_id=delta.id,
                    decision_type="REJECT",
                    payload_json=delta.payload_json,
                    reason=payload.reason or "manual reject",
                    created_by=user_id,
                )
            )

        self.delta_repo.session.flush()
        self.delta_repo.session.refresh(delta)
        return MemoryDeltaDecisionResponse(
            delta=self._to_delta_response(delta),
            merge_decision=self._to_decision_response(merge_decision) if merge_decision else None,
        )

    def _apply_delta_to_memory(self, delta: MemoryDelta) -> None:
        latest = self.memory_repo.get_latest_by_type(str(delta.project_id), delta.delta_type)
        latest_version = int(latest.version_no) if latest else 0
        merged_summary = self._merge_summary(latest.summary_json if latest else None, delta.payload_json)
        memory = Memory(
            tenant_id=delta.tenant_id,
            project_id=delta.project_id,
            memory_type=delta.delta_type,
            summary_json=merged_summary,
            version_no=latest_version + 1,
        )
        self.memory_repo.add(memory)

    def _build_project_chapter_corpus(self, project_id: str) -> tuple[str, int]:
        session = self.memory_repo.session
        from plotweaver_api.db.models import Chapter

        chapters_stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .where(Chapter.deleted_at.is_(None))
            .order_by(Chapter.order_index.asc(), Chapter.created_at.asc())
        )
        chapters = list(session.scalars(chapters_stmt).all())
        parts: list[str] = []
        for chapter in chapters:
            ver_stmt = (
                select(ChapterVersion)
                .where(ChapterVersion.chapter_id == chapter.id)
                .where(ChapterVersion.deleted_at.is_(None))
                .order_by(ChapterVersion.version_no.desc())
                .limit(1)
            )
            latest = session.scalar(ver_stmt)
            content = ""
            if latest is not None:
                try:
                    content = self.storage.get_text(latest.storage_key).strip()
                except Exception:
                    content = ""
            parts.append(f"## 第{chapter.order_index}章 {chapter.title}\n{content or '（本章暂无正文）'}")
        return "\n\n".join(parts).strip(), len(chapters)

    def _summarize_characters(self, chapter_corpus: str, project_id: str) -> tuple[dict[str, Any], str, str | None]:
        prompt = render_prompt("memory_characters.txt", all_chapters_text=chapter_corpus)
        payload, err = self._call_llm_json(
            system_prompt="你是角色设定整理助手。请严格输出 JSON 对象。",
            user_prompt=prompt,
            temperature=0.2,
        )
        if payload and isinstance(payload.get("characters"), list):
            normalized = self._normalize_character_cards(payload.get("characters") or [])
            if normalized:
                return {"source": "LLM", "characters": normalized}, "LLM", None
            fallback = self._fallback_character_cards(project_id)
            if not fallback:
                fallback = self._fallback_character_cards_from_corpus(chapter_corpus)
            return {"source": "FALLBACK", "characters": fallback}, "FALLBACK", "EMPTY_CHARACTERS_AFTER_NORMALIZE"
        fallback = self._fallback_character_cards(project_id)
        if not fallback:
            fallback = self._fallback_character_cards_from_corpus(chapter_corpus)
        reason = err or "INVALID_CHARACTERS_PAYLOAD"
        return {"source": "FALLBACK", "characters": fallback}, "FALLBACK", reason

    def _summarize_world_rules(self, chapter_corpus: str) -> tuple[dict[str, Any], str, str | None]:
        prompt = render_prompt("memory_world_rules.txt", all_chapters_text=chapter_corpus)
        text, err = self._call_llm_text(
            system_prompt="你是世界观规则整理助手。仅输出有序列表。",
            user_prompt=prompt,
            temperature=0.2,
        )
        lines = self._parse_numbered_lines(text)
        if not lines:
            lines = self._fallback_world_rules(chapter_corpus)
            return {"rules": lines}, "FALLBACK", (err or "EMPTY_WORLD_RULE_LINES")
        return {"rules": lines}, "LLM", None

    def _summarize_story(self, chapter_corpus: str) -> tuple[dict[str, Any], str, str | None]:
        prompt = render_prompt("memory_story_so_far.txt", all_chapters_text=chapter_corpus)
        text, err = self._call_llm_text(
            system_prompt="你是剧情摘要整理助手。仅输出有序列表。",
            user_prompt=prompt,
            temperature=0.2,
        )
        lines = self._parse_numbered_lines(text)
        if not lines:
            lines = self._fallback_story(chapter_corpus)
            return {"milestones": lines}, "FALLBACK", (err or "EMPTY_STORY_MILESTONES")
        return {"milestones": lines}, "LLM", None

    def _upsert_summary(self, project_id: str, memory_type: str, summary_json: dict[str, Any], user_id: str | None) -> tuple[bool, int]:
        max_retry = 1
        for attempt in range(max_retry + 1):
            latest = self.memory_repo.get_latest_by_type(project_id, memory_type)
            latest_version = int(latest.version_no) if latest else 0
            if latest and self._hash_any(latest.summary_json) == self._hash_any(summary_json):
                return False, latest_version

            memory = Memory(
                tenant_id=latest.tenant_id if latest else self._resolve_tenant_id(project_id),
                project_id=project_id,
                memory_type=memory_type,
                summary_json=summary_json,
                version_no=latest_version + 1,
                created_by=user_id,
            )
            try:
                self.memory_repo.add(memory)
                return True, latest_version + 1
            except IntegrityError:
                self.memory_repo.session.rollback()
                if attempt >= max_retry:
                    raise
                continue
        return False, 0

    def _resolve_tenant_id(self, project_id: str) -> str:
        from plotweaver_api.db.models import Project

        project = self.memory_repo.session.get(Project, project_id)
        if project is None:
            raise NotFoundError("Project not found", details={"project_id": project_id})
        return str(project.tenant_id)

    def _fallback_character_cards(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.character_repo.list_by_project(project_id, limit=50, offset=0)
        cards: list[dict[str, Any]] = []
        for row in rows:
            card = row.card_json if isinstance(row.card_json, dict) else {}
            aliases = [str(x).strip() for x in (row.aliases_json or []) if str(x).strip()]
            cards.append(
                {
                    "character_id": row.character_id,
                    "canonical_name": row.canonical_name,
                    "display_name": row.display_name,
                    "aliases": aliases,
                    "tags": card.get("tags", []),
                    "role": card.get("role", ""),
                    "age": card.get("age", 0) or 0,
                    "personality": card.get("personality", []),
                    "background": card.get("background", []),
                    "abilities": card.get("abilities", []),
                    "limitations": card.get("limitations", []),
                    "motivation": card.get("motivation", []),
                    "key_memories": card.get("key_memories", []),
                    "story_function": card.get("story_function", []),
                    "beliefs": card.get("beliefs", []),
                    "current_status": card.get("current_status", ""),
                    "relationships": card.get("relationships", []),
                    "identities": card.get("identities", []),
                    "ambiguity": card.get("ambiguity", []),
                    "merge_status": row.merge_status or "CONFIRMED",
                }
            )
            if len(cards) >= 20:
                break
        return self._sanitize_character_cards(cards)

    @staticmethod
    def _fallback_character_cards_from_corpus(corpus: str) -> list[dict[str, Any]]:
        context_map = MemoryService._extract_name_contexts(corpus)
        freq: dict[str, int] = {}
        patterns = [
            r"([\u4e00-\u9fff]{2,4})(?=说|问|道|答|喊|叫|看向|盯着|点头|摇头)",
            r"(?:名叫|叫做|叫)([\u4e00-\u9fff]{2,4})",
            r"([\u4e00-\u9fff]{2,4})(?=同学|老师|学长|学姐|会长|队长|警官)",
        ]
        for pattern in patterns:
            for token in re.findall(pattern, corpus):
                name = str(token).strip()
                if not MemoryService._looks_like_character_name(name):
                    continue
                freq[name] = freq.get(name, 0) + 1

        if not freq:
            for token in re.findall(r"[\u4e00-\u9fff]{2,3}", corpus):
                name = str(token).strip()
                if not MemoryService._looks_like_character_name(name):
                    continue
                freq[name] = freq.get(name, 0) + 1

        ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        cards: list[dict[str, Any]] = []
        for name, _ in ranked:
            snippets = context_map.get(name, [])
            role = MemoryService._guess_role_from_context(name, snippets)
            cards.append(
                {
                    "character_id": None,
                    "canonical_name": name,
                    "display_name": name,
                    "aliases": [],
                    "tags": [],
                    "role": role,
                    "age": 0,
                    "personality": [],
                    "background": [],
                    "abilities": [],
                    "limitations": [],
                    "motivation": [],
                    "key_memories": snippets[:3],
                    "story_function": [],
                    "beliefs": [],
                    "current_status": "",
                    "relationships": MemoryService._extract_relationships(name, snippets),
                    "identities": [],
                    "ambiguity": [],
                    "merge_status": "UNCONFIRMED",
                }
            )
        if not cards:
            cards.append(
                {
                    "character_id": None,
                    "canonical_name": "主角",
                    "display_name": "主角",
                    "aliases": [],
                    "tags": [],
                    "role": "主角",
                    "age": 0,
                    "personality": [],
                    "background": [],
                    "abilities": [],
                    "limitations": [],
                    "motivation": [],
                    "key_memories": [],
                    "story_function": [],
                    "beliefs": [],
                    "current_status": "",
                    "relationships": [],
                    "identities": [],
                    "ambiguity": [],
                    "merge_status": "UNCONFIRMED",
                }
            )
        return MemoryService._sanitize_character_cards(cards)

    @staticmethod
    def _extract_name_contexts(corpus: str) -> dict[str, list[str]]:
        sentence_candidates = re.split(r"[。！？!\?\n]", corpus)
        sentences = [s.strip() for s in sentence_candidates if s.strip()]
        result: dict[str, list[str]] = {}
        for sent in sentences:
            names = set(re.findall(r"[\u4e00-\u9fff]{2,3}", sent))
            valid_names = [n for n in names if MemoryService._looks_like_character_name(n)]
            for name in valid_names:
                arr = result.setdefault(name, [])
                if len(arr) < 5 and sent not in arr:
                    arr.append(sent[:120])
        return result

    @staticmethod
    def _guess_role_from_context(name: str, snippets: list[str]) -> str:
        role_map = {
            "会长": "学生会会长",
            "老师": "教师",
            "学姐": "学姐",
            "学长": "学长",
            "警官": "警官",
            "主角": "主角",
        }
        merged = " ".join(snippets)
        for k, v in role_map.items():
            if k in merged:
                return v
        if any(word in merged for word in ["我", "第一人称"]):
            return "主角相关"
        return ""

    @staticmethod
    def _extract_relationships(name: str, snippets: list[str]) -> list[str]:
        rels: list[str] = []
        for sent in snippets:
            patterns = [
                rf"{re.escape(name)}[与和对跟]([\u4e00-\u9fff]{{2,3}})",
                rf"([\u4e00-\u9fff]{{2,3}})[与和对跟]{re.escape(name)}",
            ]
            others: list[str] = []
            for pattern in patterns:
                for cand in re.findall(pattern, sent):
                    other = str(cand).strip()
                    if other == name:
                        continue
                    if not MemoryService._looks_like_character_name(other):
                        continue
                    others.append(other)
            for other in others[:2]:
                rel = f"与{other}存在互动"
                if rel not in rels:
                    rels.append(rel)
            if len(rels) >= 3:
                break
        return rels

    @staticmethod
    def _looks_like_character_name(name: str) -> bool:
        name = (name or "").strip()
        if len(name) < 2 or len(name) > 8:
            return False
        if not re.fullmatch(r"[\u4e00-\u9fff·]+", name):
            return False
        if len(name) > 3 and "·" not in name:
            return False
        if "·" in name and len(name.replace("·", "")) < 2:
            return False
        stopwords = {
            "今天", "然后", "已经", "一个", "没有", "我们", "他们", "她们", "自己", "如果", "因为",
            "但是", "这个", "那个", "这里", "那里", "学校", "章节", "主角", "故事", "世界", "规则",
            "什么", "一下", "开始", "下来", "下一秒", "三天", "的东西", "我问", "你说", "他说", "她说",
            "停摆碎片", "现在", "之后", "之前", "时候", "事情", "问题", "感觉", "地方", "声音", "有人",
            "我不知", "可我知", "都不该知", "一切都在", "低声", "准确地", "压低声音",
            "我们都", "他们都", "她们都", "不应该", "不知道", "不该知",
        }
        if name in stopwords:
            return False
        if name.startswith(("我", "你", "他", "她", "它", "这", "那", "有", "无", "可", "都")):
            return False
        if name.endswith(("地", "得", "了", "着", "过", "吗", "吧", "啊", "呢")):
            return False
        banned_suffix = ("东西", "一下", "时候", "问题", "事情", "规则", "世界", "章节", "二年", "得像", "竟上")
        if any(name.endswith(suf) for suf in banned_suffix):
            return False
        banned_chars = {"上", "下", "里", "外", "年", "月", "日", "像", "得"}
        if any(ch in name for ch in banned_chars) and "·" not in name:
            return False
        # Chinese personal names are usually 2-3 chars and commonly start with a surname.
        if "·" not in name and len(name) in {2, 3} and name[0] not in MemoryService._COMMON_SURNAMES:
            return False
        return True

    @staticmethod
    def _sanitize_character_cards(raw_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _safe_int(value: Any, default: int = 0) -> int:
            try:
                if value is None:
                    return default
                if isinstance(value, bool):
                    return default
                text = str(value).strip()
                if not text:
                    return default
                if re.fullmatch(r"-?\d+", text):
                    return int(text)
            except Exception:
                return default
            return default

        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_cards:
            if not isinstance(item, dict):
                continue
            canonical = str(item.get("canonical_name") or item.get("display_name") or "").strip()
            display = str(item.get("display_name") or canonical).strip()
            if not MemoryService._looks_like_character_name(canonical):
                continue
            if not MemoryService._looks_like_character_name(display):
                display = canonical
            dedupe_key = canonical.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            cleaned.append(
                {
                    "character_id": item.get("character_id"),
                    "canonical_name": canonical,
                    "display_name": display,
                    "aliases": [str(x).strip() for x in (item.get("aliases") or []) if str(x).strip()],
                    "tags": [str(x).strip() for x in (item.get("tags") or []) if str(x).strip()],
                    "role": str(item.get("role") or "").strip(),
                    "age": _safe_int(item.get("age"), default=0),
                    "personality": [str(x).strip() for x in (item.get("personality") or []) if str(x).strip()],
                    "background": [str(x).strip() for x in (item.get("background") or []) if str(x).strip()],
                    "abilities": [str(x).strip() for x in (item.get("abilities") or []) if str(x).strip()],
                    "limitations": [str(x).strip() for x in (item.get("limitations") or []) if str(x).strip()],
                    "motivation": [str(x).strip() for x in (item.get("motivation") or []) if str(x).strip()],
                    "key_memories": [str(x).strip() for x in (item.get("key_memories") or []) if str(x).strip()],
                    "story_function": [str(x).strip() for x in (item.get("story_function") or []) if str(x).strip()],
                    "beliefs": [str(x).strip() for x in (item.get("beliefs") or []) if str(x).strip()],
                    "current_status": str(item.get("current_status") or "").strip(),
                    "relationships": item.get("relationships") or [],
                    "identities": [str(x).strip() for x in (item.get("identities") or []) if str(x).strip()],
                    "ambiguity": [str(x).strip() for x in (item.get("ambiguity") or []) if str(x).strip()],
                    "merge_status": str(item.get("merge_status") or "UNCONFIRMED"),
                }
            )
        return cleaned[:20]

    @staticmethod
    def _normalize_character_cards(raw_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _safe_int(value: Any, default: int = 0) -> int:
            try:
                if value is None:
                    return default
                if isinstance(value, bool):
                    return default
                text = str(value).strip()
                if not text:
                    return default
                if re.fullmatch(r"-?\d+", text):
                    return int(text)
            except Exception:
                return default
            return default

        normalized: list[dict[str, Any]] = []
        for item in raw_cards:
            if not isinstance(item, dict):
                continue
            canonical = str(item.get("canonical_name") or item.get("display_name") or item.get("name") or "").strip()
            display = str(item.get("display_name") or canonical).strip()
            if not canonical and not display:
                continue
            relationships_raw = item.get("relationships")
            relationships: list[str]
            if isinstance(relationships_raw, list):
                relationships = [str(x).strip() for x in relationships_raw if str(x).strip()]
            elif relationships_raw:
                relationships = [str(relationships_raw).strip()]
            else:
                relationships = []

            normalized.append(
                {
                    "character_id": item.get("character_id"),
                    "canonical_name": canonical or display,
                    "display_name": display or canonical,
                    "aliases": [str(x).strip() for x in (item.get("aliases") or []) if str(x).strip()],
                    "tags": [str(x).strip() for x in (item.get("tags") or []) if str(x).strip()],
                    "role": str(item.get("role") or "").strip(),
                    "age": _safe_int(item.get("age"), default=0),
                    "personality": [str(x).strip() for x in (item.get("personality") or []) if str(x).strip()],
                    "background": [str(x).strip() for x in (item.get("background") or []) if str(x).strip()],
                    "abilities": [str(x).strip() for x in (item.get("abilities") or []) if str(x).strip()],
                    "limitations": [str(x).strip() for x in (item.get("limitations") or []) if str(x).strip()],
                    "motivation": [str(x).strip() for x in (item.get("motivation") or []) if str(x).strip()],
                    "key_memories": [str(x).strip() for x in (item.get("key_memories") or []) if str(x).strip()],
                    "story_function": [str(x).strip() for x in (item.get("story_function") or []) if str(x).strip()],
                    "beliefs": [str(x).strip() for x in (item.get("beliefs") or []) if str(x).strip()],
                    "current_status": str(item.get("current_status") or "").strip(),
                    "relationships": relationships,
                    "identities": [str(x).strip() for x in (item.get("identities") or []) if str(x).strip()],
                    "ambiguity": [str(x).strip() for x in (item.get("ambiguity") or []) if str(x).strip()],
                    "merge_status": str(item.get("merge_status") or "UNCONFIRMED"),
                }
            )
        return normalized[:50]

    @staticmethod
    def _is_low_quality_character_cards(cards: list[dict[str, Any]]) -> bool:
        if not cards:
            return True
        informative_count = 0
        for card in cards:
            role = str(card.get("role") or "").strip()
            key_memories = card.get("key_memories") or []
            relationships = card.get("relationships") or []
            personality = card.get("personality") or []
            background = card.get("background") or []
            has_info = bool(role) or bool(key_memories) or bool(relationships) or bool(personality) or bool(background)
            if has_info:
                informative_count += 1
        # If almost all cards are only names with empty attributes, treat as low quality.
        return informative_count < max(1, len(cards) // 3)

    @staticmethod
    def _parse_numbered_lines(text: str | None) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        for raw in text.splitlines():
            item = raw.strip()
            if not item:
                continue
            item = re.sub(r"^\d+\.\s*", "", item)
            item = re.sub(r"^-\s*", "", item)
            item = item.strip()
            if item:
                lines.append(item)
        return lines[:20]

    @staticmethod
    def _fallback_world_rules(corpus: str) -> list[str]:
        lines = [ln.strip() for ln in corpus.splitlines() if ln.strip()]
        picked = [ln for ln in lines if any(k in ln for k in ["规则", "必须", "不能", "学院", "禁忌", "组织"])]
        if not picked:
            picked = lines[:10]
        return picked[:12]

    @staticmethod
    def _fallback_story(corpus: str) -> list[str]:
        lines = [ln.strip() for ln in corpus.splitlines() if ln.strip() and not ln.startswith("##")]
        return lines[:12] if lines else ["暂无可提取剧情摘要。"]

    def _call_llm_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> tuple[str | None, str | None]:
        if settings.ark_api_key == "" or settings.ark_model == "":
            return None, "MISSING_ARK_CONFIG"
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)
            resp = client.chat.completions.create(
                model=settings.ark_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            content = resp.choices[0].message.content
            if not content:
                return None, "EMPTY_LLM_RESPONSE"
            return content.strip(), None
        except Exception as exc:
            return None, f"LLM_CALL_FAILED: {exc}"

    def _call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_retry: int = 1,
    ) -> tuple[dict[str, Any] | None, str | None]:
        text, err = self._call_llm_text(system_prompt, user_prompt, temperature=temperature)
        if text is None:
            return None, err
        attempts = 1 + max_retry
        current_text = text
        for _ in range(attempts):
            parsed = self._extract_json_object(current_text)
            if parsed is not None:
                return parsed, None
            retry_text, retry_err = self._call_llm_text(
                system_prompt,
                "请只输出 JSON 对象，不要输出额外解释。",
                temperature=0,
            )
            current_text = retry_text or ""
            err = retry_err or err
        return None, err or "INVALID_JSON_LLM_RESPONSE"

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        raw = text.strip()
        candidates = [raw]
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(raw[start : end + 1])
        for item in candidates:
            try:
                data = json.loads(item)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        return None

    @staticmethod
    def _hash_any(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _merge_summary(base: dict | list | None, delta_payload: dict) -> list[str]:
        base_lines: list[str] = []
        if isinstance(base, list):
            base_lines = [str(item).strip() for item in base if str(item).strip()]
        elif isinstance(base, dict):
            for value in base.values():
                if isinstance(value, list):
                    base_lines.extend(str(item).strip() for item in value if str(item).strip())
                elif value:
                    base_lines.append(str(value).strip())

        delta_lines: list[str] = []
        for value in delta_payload.values():
            if isinstance(value, list):
                delta_lines.extend(str(item).strip() for item in value if str(item).strip())
            elif value:
                delta_lines.append(str(value).strip())

        seen = {line for line in base_lines if line}
        merged = [line for line in base_lines if line]
        for line in delta_lines:
            if line and line not in seen:
                merged.append(line)
                seen.add(line)
        return merged[:100]

    @staticmethod
    def _to_character_response(row: Character) -> CharacterResponse:
        return CharacterResponse(
            id=str(row.id),
            project_id=str(row.project_id),
            character_id=row.character_id,
            canonical_name=row.canonical_name,
            display_name=row.display_name,
            aliases_json=row.aliases_json,
            merge_status=row.merge_status,
            card_json=row.card_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_delta_response(row: MemoryDelta) -> MemoryDeltaResponse:
        return MemoryDeltaResponse(
            id=str(row.id),
            run_id=str(row.run_id),
            project_id=str(row.project_id),
            delta_type=row.delta_type,
            payload_json=row.payload_json,
            gate_status=row.gate_status,
            risk_level=row.risk_level,
            applied_at=row.applied_at,
            applied_by=str(row.applied_by) if row.applied_by else None,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_decision_response(row: MergeDecision) -> MergeDecisionResponse:
        return MergeDecisionResponse(
            id=str(row.id),
            project_id=str(row.project_id),
            run_id=str(row.run_id) if row.run_id else None,
            delta_id=str(row.delta_id) if row.delta_id else None,
            decision_type=row.decision_type,
            payload_json=row.payload_json,
            reason=row.reason,
            created_at=row.created_at,
        )
