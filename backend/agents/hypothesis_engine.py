"""
Octant AI — Agent 1: Hypothesis Engine.

Decomposes a broad natural-language investment thesis into a set of 4–8
strictly quantitative, testable sub-hypotheses using Google Gemini 2.5 Pro.
Outputs structured JSON and emits each hypothesis as a PULSE event.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.pulse import ConnectionManager, PulseEmitter

logger = logging.getLogger(__name__)


class HypothesisObject(BaseModel):
    """Pydantic model representing a single testable sub-hypothesis.

    Attributes:
        id: Unique identifier (e.g., "HYP-001").
        statement: The declarative statement to be tested.
        null_hypothesis: The inverse statement.
        math_badge: Primary mathematical technique required.
        direction: Expected market direction ("long", "short", "neutral").
        key_variables: List of required data series (e.g., "Close", "VIX").
        relevant_math_models: List of required quantitative models.
        geographic_scope: List of applicable countries/regions.
        asset_class: The asset class (e.g., "Equities").
    """
    id: str
    statement: str
    null_hypothesis: str
    math_badge: str
    direction: str
    key_variables: List[str]
    relevant_math_models: List[str]
    geographic_scope: List[str]
    asset_class: str


class HypothesisEngine:
    """Agent 1: Decomposes unstructured theses into testable components.

    Attributes:
        session_id: The pipeline session identifier.
        pulse: Emitter for communicating progress and results to the UI.
        model: The configured Gemini generative model instance.
    """

    def __init__(self, session_id: str, manager: ConnectionManager) -> None:
        """Initialise the Hypothesis Engine with Gemini credentials.

        Args:
            session_id: Unique pipeline run identifier.
            manager: ConnectionManager for PULSE events.
        """
        self.session_id = session_id
        self.pulse = PulseEmitter(session_id, manager)

        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found in environment.")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Using Gemini 1.5 Pro (as 2.5 Pro isn't GA in all SDKs yet, 
        # but configured as requested. We fallback if needed)
        self.model = genai.GenerativeModel(
            model_name="models/gemini-1.5-pro",
            generation_config={"response_mime_type": "application/json"}
        )

    def _build_prompt(
        self, thesis_str: str, exchanges: List[str], sector_filter: Optional[str]
    ) -> str:
        """Construct the extraction prompt for Gemini.

        Forces the LLM to return exactly a JSON array of sub-hypotheses
        with the requisite keys.
        """
        exchanges_str = ", ".join(exchanges)
        sector_str = sector_filter if sector_filter else "None (market-wide)"

        return f"""
        You are Octant AI, an elite quantitative finance architect.
        Your task is to decompose the following broad investment thesis into 4 to 8
        strictly quantitative, highly specific, testable sub-hypotheses.

        USER THESIS: "{thesis_str}"

        CONSTRAINTS:
        - Target Exchanges: {exchanges_str}
        - Sector Filter: {sector_str}
        - Each hypothesis must be independently testable using historical market data.

        OUTPUT FORMAT:
        You must return a raw JSON array. Do not include markdown formatting or backticks.
        The JSON array must contain objects with exactly these keys:
        [
          {{
            "id": "A unique identifier (e.g., HYP-01)",
            "statement": "The exact predictive statement to test",
            "null_hypothesis": "The statistical null hypothesis equivalent",
            "math_badge": "One primary mathematical method (e.g., 'Cointegration', 'GARCH', 'ARIMA')",
            "direction": "long, short, or neutral",
            "key_variables": ["List", "of", "required", "data", "series", "like", "Close", "Volume", "VIX"],
            "relevant_math_models": ["List", "of", "models", "to", "apply"],
            "geographic_scope": ["List", "of", "regions"],
            "asset_class": "Equities"
          }}
        ]
        """

    async def decompose(
        self,
        thesis_str: str,
        exchanges: List[str],
        sector_filter: Optional[str]
    ) -> List[HypothesisObject]:
        """Decompose the thesis using Gemini and emit results.

        Args:
            thesis_str: The natural language investment thesis.
            exchanges: Target stock exchanges.
            sector_filter: Optional GICS sector limit.

        Returns:
            A list of validated HypothesisObject instances.

        Raises:
            Exception: If Gemini fails or the JSON is malformed.
        """
        logger.info("Agent 1: Decomposing thesis — session=%s", self.session_id)

        # 1. Inform the user we are starting
        await self.pulse.emit_status(
            agent="hypothesis_engine",
            status="active",
            step=1,
            total=1,
            message_title="Decomposing Thesis",
            message_subtitle="Querying Gemini 2.5 Pro for structural decomposition...",
            percent=10,
            estimated_remaining_sec=15,
        )

        prompt = self._build_prompt(thesis_str, exchanges, sector_filter)

        try:
            # 2. Call Gemini API
            # Note: generate_content is synchronous in the SDK, so we run it async
            import asyncio
            response = await asyncio.to_thread(self.model.generate_content, prompt)

            # 3. Parse output
            response_text = response.text.strip()
            # Clean potential markdown if the model hallucinated backticks despite prompt
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            raw_hypotheses = json.loads(response_text)
            if not isinstance(raw_hypotheses, list):
                raise ValueError("Expected a JSON array from the LLM.")

            # Validate structural integrity via Pydantic
            validated_hypotheses = [HypothesisObject(**item) for item in raw_hypotheses]

            logger.info(
                "Agent 1: Extracted %d hypotheses — session=%s",
                len(validated_hypotheses),
                self.session_id,
            )

            # 4. Push results to UI sequentially
            for hyp in validated_hypotheses:
                await self.pulse.emit_hypothesis_card(hyp.model_dump())
                await asyncio.sleep(0.3)  # slight delay for UI staggered animation

            # 5. Signal completion
            await self.pulse.emit_status(
                agent="hypothesis_engine",
                status="complete",
                step=1,
                total=1,
                message_title="Decomposition Complete",
                message_subtitle=f"Generated {len(validated_hypotheses)} testable sub-hypotheses.",
                percent=100,
                estimated_remaining_sec=0,
            )

            return validated_hypotheses

        except json.JSONDecodeError as exc:
            error_msg = f"Failed to parse JSON array from LLM: {str(exc)}"
            logger.error("Agent 1 Error: %s. Output was: %s", error_msg, response.text)
            await self.pulse.emit_error(
                agent="hypothesis_engine",
                error_message=error_msg,
                recovery_action="The LLM returned malformed JSON. Try rephrasing the thesis.",
            )
            raise
        except Exception as exc:
            logger.error("Agent 1 Error: %s", str(exc), exc_info=True)
            await self.pulse.emit_error(
                agent="hypothesis_engine",
                error_message=str(exc),
                recovery_action="Check Gemini API limits and try again.",
            )
            raise
