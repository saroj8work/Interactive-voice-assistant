"""
Markdown Domain Knowledge Ingestion and Search Engine.
Loads, parses, sections, and retrieves domain knowledge from .md files.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings

DOMAIN_MD_DEFAULT = settings.base_dir / "data" / "domain_knowledge.md"


class KnowledgeSection(BaseModel):
    id: str
    title: str
    level: int
    content: str
    summary: str
    keywords: List[str] = Field(default_factory=list)


class KnowledgeQueryResult(BaseModel):
    query: str
    found: bool
    top_section: Optional[KnowledgeSection] = None
    all_matches: List[KnowledgeSection] = Field(default_factory=list)
    answer: str
    score: float = 0.0


class MarkdownDomainKnowledge:
    """
    Parses and indexes a Markdown file to serve as the agent's domain knowledge base.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = Path(file_path or os.getenv("DOMAIN_KNOWLEDGE_FILE", str(DOMAIN_MD_DEFAULT)))
        self.sections: List[KnowledgeSection] = []
        self.load()

    def load(self) -> bool:
        """Loads and parses the markdown file into indexed sections."""
        if not self.file_path.exists():
            # If file doesn't exist, create an empty placeholder
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text("# Domain Knowledge Base\n\nNo domain knowledge loaded.", encoding="utf-8")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            self.sections = self._parse_markdown(raw_text)
            return True
        except Exception as e:
            print(f"Error loading domain knowledge markdown: {e}")
            return False

    def update_markdown(self, content: str) -> bool:
        """Updates the markdown file content and reloads the index."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.sections = self._parse_markdown(content)
            return True
        except Exception as e:
            print(f"Error updating domain knowledge markdown: {e}")
            return False

    def _parse_markdown(self, text: str) -> List[KnowledgeSection]:
        """Splits markdown text by headers (#, ##, ###) into structured sections."""
        lines = text.split("\n")
        sections: List[KnowledgeSection] = []
        current_title = "Overview"
        current_level = 1
        current_lines: List[str] = []
        section_idx = 1

        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if header_match:
                # Flush previous section
                if current_lines:
                    content_str = "\n".join(current_lines).strip()
                    if content_str:
                        sections.append(
                            self._create_section(
                                sec_id=f"sec_{section_idx}",
                                title=current_title,
                                level=current_level,
                                content=content_str,
                            )
                        )
                        section_idx += 1
                    current_lines = []

                current_level = len(header_match.group(1))
                current_title = header_match.group(2).strip()
            else:
                current_lines.append(line)

        # Flush trailing section
        if current_lines:
            content_str = "\n".join(current_lines).strip()
            if content_str:
                sections.append(
                    self._create_section(
                        sec_id=f"sec_{section_idx}",
                        title=current_title,
                        level=current_level,
                        content=content_str,
                    )
                )

        return sections

    def _create_section(self, sec_id: str, title: str, level: int, content: str) -> KnowledgeSection:
        # Extract summary: first 2 non-empty lines
        clean_lines = [l.strip("- *#") for l in content.split("\n") if l.strip()]
        summary = " ".join(clean_lines[:2]) if clean_lines else content[:150]

        # Extract keywords
        words = re.findall(r"\b[A-Za-z0-9_]{3,}\b", f"{title} {content}".lower())
        stopwords = {
            "the", "and", "for", "with", "this", "that", "from", "are", "can",
            "you", "your", "must", "will", "all", "any", "not", "have", "has",
        }
        keywords = list(dict.fromkeys([w for w in words if w not in stopwords]))[:15]

        return KnowledgeSection(
            id=sec_id,
            title=title,
            level=level,
            content=content,
            summary=summary,
            keywords=keywords,
        )

    def query(self, query_text: str, top_k: int = 3) -> KnowledgeQueryResult:
        """
        Searches the domain knowledge markdown sections for relevant answers.
        Uses multi-token keyword relevance and title boosting.
        """
        clean_q = query_text.lower().strip()
        q_tokens = re.findall(r"\b\w{3,}\b", clean_q)

        scored: List[tuple[KnowledgeSection, float]] = []

        for sec in self.sections:
            score = 0.0
            sec_title_lower = sec.title.lower()
            sec_content_lower = sec.content.lower()

            # Exact phrase match in title or content
            if clean_q in sec_title_lower:
                score += 5.0
            elif clean_q in sec_content_lower:
                score += 3.0

            # Token overlap scoring
            for token in q_tokens:
                if token in sec_title_lower:
                    score += 2.0
                if token in sec.keywords:
                    score += 1.5
                if token in sec_content_lower:
                    score += 0.8

            if score > 0.5:
                scored.append((sec, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            return KnowledgeQueryResult(
                query=query_text,
                found=False,
                top_section=None,
                all_matches=[],
                answer=f"I couldn't find specific documentation on '{query_text}' in the domain knowledge base.",
                score=0.0,
            )

        top_sec, top_score = scored[0]
        matches = [s[0] for s in scored[:top_k]]

        # Construct answer from top section
        answer = f"According to the {top_sec.title} documentation: {top_sec.summary}"

        return KnowledgeQueryResult(
            query=query_text,
            found=True,
            top_section=top_sec,
            all_matches=matches,
            answer=answer,
            score=round(top_score, 2),
        )


domain_knowledge = MarkdownDomainKnowledge()

