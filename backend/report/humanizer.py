"""Report humanizer — detects and rewrites AI writing patterns."""

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# 25 AI vocabulary patterns to detect and eliminate
AI_PATTERNS = [
    r"\bdelve\b",
    r"\btapestry\b",
    r"\blandscape\b",
    r"\brealm\b",
    r"\bunderscores?\b",
    r"\bfostering?\b",
    r"\bpivotal\b",
    r"\bcrucial\b",
    r"\bparamount\b",
    r"\bseamless(?:ly)?\b",
    r"\bholistic(?:ally)?\b",
    r"\brobust\b",
    r"\bnovel\b",
    r"\bintricate\b",
    r"\bculminates?\b",
    r"\bburgeoning\b",
    r"\bmeticulous(?:ly)?\b",
    r"\belucidates?\b",
    r"\bstakeholders?\b",
    r"\bbespoke\b",
    r"\bin conclusion\b",
    r"\bit is worth noting\b",
    r"\boverall\b",
    r"\bnotably\b",
    r"\bmoreover\b",
]

SIGNIFICANCE_INFLATION = [
    r"\bgroundbreaking\b",
    r"\bpioneer(?:ing)?\b",
    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\bunprecedented\b",
    r"\bparadigm[- ]shift\b",
]

FILLER_PHRASES = [
    r"it is important to note that",
    r"in today'?s (?:rapidly )?(?:evolving|changing)",
    r"a (?:wide )?(?:variety|range|myriad) of",
    r"play(?:s|ing)? a (?:crucial|key|vital|pivotal) role",
]

ALL_PATTERNS = AI_PATTERNS + SIGNIFICANCE_INFLATION + FILLER_PHRASES
COMPILED = [re.compile(p, re.IGNORECASE) for p in ALL_PATTERNS]


def detect_ai_patterns(text: str) -> list[str]:
    """Return list of AI vocabulary matches found in text."""
    hits = []
    for pattern in COMPILED:
        matches = pattern.findall(text)
        if matches:
            hits.extend(matches)
    return hits


class ReportHumanizer:
    """Two-pass system: regex detection + LLM rewrite."""

    def __init__(self, llm_provider: "LLMProvider"):
        self.llm = llm_provider

    async def humanize(self, text: str) -> str:
        """Run text through the humanizer pipeline.

        Pass 1: Regex scan for AI vocabulary.
        Pass 2: LLM rewrite if patterns detected.
        """
        if not text or len(text) < 50:
            return text

        hits = detect_ai_patterns(text)
        if not hits:
            logger.debug("Humanizer: no AI patterns detected, text unchanged")
            return text

        logger.info("Humanizer: detected %d AI patterns, rewriting", len(hits))

        rewrite_prompt = (
            "Rewrite the following academic text to sound more natural and human-written. "
            "Remove AI-sounding vocabulary and filler phrases. "
            "Keep the technical accuracy, data, statistics, and citations intact. "
            "Do not add new information. Do not change any numbers or findings. "
            "Just make it read like an experienced human researcher wrote it.\n\n"
            f"Detected AI patterns to remove: {', '.join(set(hits[:10]))}\n\n"
            f"TEXT:\n{text}"
        )

        try:
            rewritten = await self.llm.generate(rewrite_prompt)
            if rewritten and len(rewritten) > len(text) * 0.3:
                return rewritten
            return text
        except Exception as exc:
            logger.error("Humanizer LLM rewrite failed: %s", exc)
            return text
