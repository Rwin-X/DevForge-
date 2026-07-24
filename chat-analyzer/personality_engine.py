"""
Chat Personality Analyzer - Personality Engine
===============================================
Combines rule-based NLP signal extraction with an optional
AI-powered narrative analysis (OpenAI or local LLM).
"""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from typing import Optional

# ── Graceful optional imports ─────────────────────────────────────────────────
try:
    from textblob import TextBlob          # type: ignore
    _HAS_TEXTBLOB = True
except ImportError:
    _HAS_TEXTBLOB = False

try:
    import openai                          # type: ignore
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

try:
    import nltk                            # type: ignore
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    _HAS_NLTK = True
    try:
        _STOPWORDS = set(stopwords.words("english"))
    except LookupError:
        try:
            nltk.download("stopwords", quiet=True)
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
            _STOPWORDS = set(stopwords.words("english"))
        except Exception:
            _STOPWORDS = set()
except ImportError:
    _HAS_NLTK = False
    _STOPWORDS = set()

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    LLM_CONTEXT_CHARS,
    RULE_WEIGHT,
    AI_WEIGHT,
    TOPIC_KEYWORDS,
    CURIOSITY_SIGNALS,
    HUMOR_SIGNALS,
    ASSERTIVE_SIGNALS,
    EMPATHY_SIGNALS,
    ANALYTICAL_SIGNALS,
    CREATIVITY_SIGNALS,
    LEADERSHIP_SIGNALS,
    INFORMAL_MARKERS,
    FORMAL_MARKERS,
)
from parser import ParsedConversation, ConversationStats


# ─── Result data structures ───────────────────────────────────────────────────

@dataclass
class PersonalityScores:
    """0-100 scores for each personality dimension."""
    curiosity: float = 0.0
    confidence: float = 0.0
    friendliness: float = 0.0
    analytical_thinking: float = 0.0
    creativity: float = 0.0
    emotional_expression: float = 0.0
    leadership: float = 0.0
    social_engagement: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "curiosity": round(self.curiosity, 1),
            "confidence": round(self.confidence, 1),
            "friendliness": round(self.friendliness, 1),
            "analytical_thinking": round(self.analytical_thinking, 1),
            "creativity": round(self.creativity, 1),
            "emotional_expression": round(self.emotional_expression, 1),
            "leadership": round(self.leadership, 1),
            "social_engagement": round(self.social_engagement, 1),
        }


@dataclass
class CommunicationStyle:
    formality: float = 50.0          # 0=very informal, 100=very formal
    friendliness: float = 50.0
    assertiveness: float = 50.0
    emotional_expression: float = 50.0
    humor_usage: float = 50.0


@dataclass
class BehaviorIndicators:
    curiosity: float = 50.0
    confidence: float = 50.0
    patience: float = 50.0
    leadership: float = 50.0
    independence: float = 50.0
    openness: float = 50.0


@dataclass
class ThinkingStyle:
    analytical: float = 50.0
    creative: float = 50.0
    practical: float = 50.0
    strategic: float = 50.0
    detail_oriented: float = 50.0


@dataclass
class TopicInterest:
    topic: str
    confidence: float          # 0-100
    mention_count: int


@dataclass
class SentimentProfile:
    overall_polarity: float    # -1 to +1
    overall_subjectivity: float
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float


@dataclass
class AIInsights:
    personality_summary: str = ""
    communication_profile: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    executive_summary: str = ""
    final_assessment: str = ""
    ai_scores: Optional[dict[str, float]] = None


@dataclass
class AnalysisResult:
    speaker: str
    scores: PersonalityScores
    communication_style: CommunicationStyle
    behavior_indicators: BehaviorIndicators
    thinking_style: ThinkingStyle
    topics: list[TopicInterest]
    sentiment: Optional[SentimentProfile]
    ai_insights: AIInsights
    stats: ConversationStats
    ai_available: bool = False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _signal_density(text_lower: str, signals: list[str]) -> float:
    """
    Return [0, 100] score based on how many signal words appear per 100 words.
    """
    words = text_lower.split()
    if not words:
        return 0.0
    hits = sum(text_lower.count(sig) for sig in signals)
    density = hits / (len(words) / 100)
    return min(100.0, density * 15)          # scale to 0-100


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _extract_messages_text(conv: ParsedConversation, speaker: str) -> str:
    msgs = [m.text for m in conv.messages if m.speaker == speaker]
    return " ".join(msgs)


# ─── Rule-based analysis ──────────────────────────────────────────────────────

def _analyze_topics(text_lower: str) -> list[TopicInterest]:
    results: list[TopicInterest] = []
    words = text_lower.split()
    total = max(len(words), 1)
    for topic, keywords in TOPIC_KEYWORDS.items():
        count = sum(text_lower.count(kw) for kw in keywords)
        if count == 0:
            continue
        confidence = min(100.0, (count / total) * 3000)
        results.append(TopicInterest(topic=topic, confidence=round(confidence, 1), mention_count=count))
    results.sort(key=lambda t: t.confidence, reverse=True)
    return results[:8]


def _analyze_sentiment(text: str) -> Optional[SentimentProfile]:
    if not _HAS_TEXTBLOB:
        return None
    blob = TextBlob(text)
    sentences = blob.sentences
    if not sentences:
        return None
    polarities = [s.sentiment.polarity for s in sentences]
    pos = sum(1 for p in polarities if p > 0.1)
    neg = sum(1 for p in polarities if p < -0.1)
    neu = len(polarities) - pos - neg
    total = max(len(polarities), 1)
    return SentimentProfile(
        overall_polarity=blob.sentiment.polarity,
        overall_subjectivity=blob.sentiment.subjectivity,
        positive_ratio=pos / total,
        negative_ratio=neg / total,
        neutral_ratio=neu / total,
    )


def _rule_based_scores(text: str, stats: ConversationStats) -> PersonalityScores:
    tl = text.lower()

    # ── Core signal densities
    curiosity_raw = _signal_density(tl, CURIOSITY_SIGNALS)
    humor_raw = _signal_density(tl, HUMOR_SIGNALS)
    assertive_raw = _signal_density(tl, ASSERTIVE_SIGNALS)
    empathy_raw = _signal_density(tl, EMPATHY_SIGNALS)
    analytical_raw = _signal_density(tl, ANALYTICAL_SIGNALS)
    creative_raw = _signal_density(tl, CREATIVITY_SIGNALS)
    leadership_raw = _signal_density(tl, LEADERSHIP_SIGNALS)

    # ── Formality (proxy for confidence / assertiveness)
    informal_score = _signal_density(tl, INFORMAL_MARKERS)
    formal_score = _signal_density(tl, FORMAL_MARKERS)
    formality = _clamp(50 + formal_score - informal_score)

    # ── Question ratio (curiosity proxy)
    q_ratio = stats.question_count / max(stats.message_count, 1)
    curiosity = _clamp((curiosity_raw * 0.6) + (min(q_ratio * 200, 40)))

    # ── Message length → detail orientation / confidence
    avg_len = stats.avg_message_length
    length_score = _clamp(min(avg_len * 5, 60))

    # ── Emoji / exclamation → friendliness / emotional expression
    emoji_ratio = stats.emoji_count / max(stats.message_count, 1)
    exc_ratio = stats.exclamation_count / max(stats.message_count, 1)
    friendliness = _clamp(30 + empathy_raw * 0.5 + min(emoji_ratio * 25, 30) + humor_raw * 0.3)
    emotional_exp = _clamp(20 + empathy_raw * 0.6 + min(emoji_ratio * 30, 30) + min(exc_ratio * 20, 20))

    # ── Confidence: assertive language + longer messages
    confidence = _clamp(formality * 0.35 + assertive_raw * 0.4 + length_score * 0.25)

    # ── Analytical
    analytical = _clamp(analytical_raw * 0.7 + length_score * 0.3)

    # ── Creativity
    creativity = _clamp(creative_raw * 0.7 + humor_raw * 0.2 + 10)

    # ── Leadership
    leadership = _clamp(leadership_raw * 0.7 + assertive_raw * 0.2 + length_score * 0.1)

    # ── Social engagement: frequency + variety
    social = _clamp(friendliness * 0.4 + curiosity * 0.3 + humor_raw * 0.3)

    return PersonalityScores(
        curiosity=curiosity,
        confidence=confidence,
        friendliness=friendliness,
        analytical_thinking=analytical,
        creativity=creativity,
        emotional_expression=emotional_exp,
        leadership=leadership,
        social_engagement=social,
    )


def _rule_based_styles(text: str, scores: PersonalityScores) -> tuple[CommunicationStyle, BehaviorIndicators, ThinkingStyle]:
    tl = text.lower()
    informal = _signal_density(tl, INFORMAL_MARKERS)
    formal = _signal_density(tl, FORMAL_MARKERS)
    formality = _clamp(50 + formal * 0.7 - informal * 0.7)

    comm = CommunicationStyle(
        formality=formality,
        friendliness=scores.friendliness,
        assertiveness=scores.confidence,
        emotional_expression=scores.emotional_expression,
        humor_usage=_clamp(_signal_density(tl, HUMOR_SIGNALS) * 1.2),
    )

    behav = BehaviorIndicators(
        curiosity=scores.curiosity,
        confidence=scores.confidence,
        patience=_clamp(60 + (50 - scores.emotional_expression) * 0.3),
        leadership=scores.leadership,
        independence=_clamp(40 + scores.confidence * 0.3 + scores.analytical_thinking * 0.2),
        openness=_clamp((scores.curiosity + scores.friendliness) / 2),
    )

    think = ThinkingStyle(
        analytical=scores.analytical_thinking,
        creative=scores.creativity,
        practical=_clamp(50 + scores.confidence * 0.2 - scores.creativity * 0.1),
        strategic=_clamp((scores.analytical_thinking + scores.leadership) / 2),
        detail_oriented=_clamp(
            _signal_density(tl, ANALYTICAL_SIGNALS) * 0.5 + min(text.split().__len__() / 5, 50)
        ),
    )
    return comm, behav, think


# ─── AI-powered analysis ──────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert psycholinguist and personality analyst. You analyze chat transcripts
and generate insightful, evidence-based personality profiles. 

IMPORTANT RULES:
1. NEVER claim certainty. Use hedged language: "may indicate", "suggests", "possibly reflects",
   "appears to", "tends to", "this could indicate".
2. Be specific and reference actual language patterns from the messages.
3. Be balanced – note both strengths and potential areas for growth.
4. Keep the profile respectful and constructive.
5. Return ONLY valid JSON, no markdown fences, no extra text.
"""

_USER_PROMPT_TEMPLATE = """\
Analyze the following chat messages from "{speaker}" and return a JSON object with exactly these keys:

{{
  "personality_summary": "2-3 paragraph personality overview using hedged language",
  "communication_profile": "1-2 paragraph description of their communication style",
  "strengths": ["strength 1 (specific, with example)", "strength 2", "strength 3", "strength 4", "strength 5"],
  "weaknesses": ["potential area 1 (framed constructively)", "potential area 2", "potential area 3"],
  "executive_summary": "1 concise sentence summary",
  "final_assessment": "1-2 paragraph concluding assessment",
  "scores": {{
    "curiosity": <0-100>,
    "confidence": <0-100>,
    "friendliness": <0-100>,
    "analytical_thinking": <0-100>,
    "creativity": <0-100>,
    "emotional_expression": <0-100>,
    "leadership": <0-100>,
    "social_engagement": <0-100>
  }}
}}

Chat messages from {speaker}:
---
{messages}
---

Statistics:
- Total messages: {msg_count}
- Average message length: {avg_len:.1f} words
- Questions asked: {q_count}
- Emojis used: {emoji_count}
"""


def _call_openai(speaker: str, messages_text: str, stats: ConversationStats) -> Optional[AIInsights]:
    if not _HAS_OPENAI or not OPENAI_API_KEY:
        return None
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = _USER_PROMPT_TEMPLATE.format(
            speaker=speaker,
            messages=messages_text[:LLM_CONTEXT_CHARS],
            msg_count=stats.message_count,
            avg_len=stats.avg_message_length,
            q_count=stats.question_count,
            emoji_count=stats.emoji_count,
        )
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        raw = response.choices[0].message.content or ""
        # Strip any accidental markdown fences
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        data = json.loads(raw)
        return AIInsights(
            personality_summary=data.get("personality_summary", ""),
            communication_profile=data.get("communication_profile", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            executive_summary=data.get("executive_summary", ""),
            final_assessment=data.get("final_assessment", ""),
            ai_scores=data.get("scores"),
        )
    except json.JSONDecodeError as e:
        warnings.warn(f"AI response was not valid JSON: {e}")
        return None
    except Exception as e:
        warnings.warn(f"OpenAI call failed: {e}")
        return None


def _fallback_insights(speaker: str, scores: PersonalityScores, stats: Optional[ConversationStats] = None) -> AIInsights:
    """Generate rule-based narrative when AI is unavailable."""
    top = max(scores.as_dict(), key=lambda k: scores.as_dict()[k])
    low = min(scores.as_dict(), key=lambda k: scores.as_dict()[k])

    trait_descriptions = {
        "curiosity": "intellectual curiosity and a desire to understand the world",
        "confidence": "self-assurance in expressing their views",
        "friendliness": "warmth and approachability",
        "analytical_thinking": "logical, structured thinking",
        "creativity": "imaginative and inventive thinking",
        "emotional_expression": "emotional openness and expressiveness",
        "leadership": "initiative and guiding tendencies",
        "social_engagement": "enthusiasm for social interaction",
    }

    summary = (
        f"{speaker}'s messages may indicate {trait_descriptions.get(top, top)}. "
        f"Their communication style possibly reflects a tendency toward "
        f"{'detailed, thoughtful responses' if (stats and stats.avg_message_length > 20) else 'concise, direct communication'}. "
        f"Based on language patterns, this person appears to prioritize "
        f"{'analytical clarity' if scores.analytical_thinking > 60 else 'interpersonal connection'}."
    )

    strengths = []
    sd = scores.as_dict()
    for trait, desc in trait_descriptions.items():
        if sd.get(trait, 0) >= 65:
            strengths.append(f"Strong {trait.replace('_', ' ')}: their messages suggest {desc}")
    if not strengths:
        strengths = ["Consistent communication style", "Clear message structure"]

    weaknesses = []
    for trait, desc in trait_descriptions.items():
        if sd.get(trait, 0) <= 35:
            weaknesses.append(
                f"May benefit from developing {trait.replace('_', ' ')} – "
                f"messages suggest limited expression of {desc}"
            )
    if not weaknesses:
        weaknesses = ["Analysis limited by available message data"]

    return AIInsights(
        personality_summary=summary,
        communication_profile=(
            f"Based on message patterns, {speaker} appears to communicate in a "
            f"{'formal' if scores.confidence > 60 else 'informal'}, "
            f"{'friendly' if scores.friendliness > 60 else 'matter-of-fact'} manner. "
            f"Their messages possibly reflect a preference for "
            f"{'substantive discussion' if scores.analytical_thinking > 50 else 'casual conversation'}."
        ),
        strengths=strengths[:5],
        weaknesses=weaknesses[:3],
        executive_summary=f"{speaker} may be characterized by {trait_descriptions.get(top, 'a distinctive communication style')}.",
        final_assessment=(
            f"Overall, the message patterns suggest {speaker} is a "
            f"{'thoughtful and analytical' if scores.analytical_thinking > 60 else 'sociable and expressive'} "
            f"communicator who possibly values "
            f"{'depth and accuracy' if scores.analytical_thinking > scores.emotional_expression else 'connection and expression'}. "
            f"Note: this assessment is based solely on chat patterns and should be interpreted with caution."
        ),
        ai_scores=None,
    )


# ─── Blend scores ─────────────────────────────────────────────────────────────

def _blend(rule: PersonalityScores, ai: Optional[dict[str, float]]) -> PersonalityScores:
    if ai is None:
        return rule
    rd, blended = rule.as_dict(), {}
    for key in rd:
        ai_val = ai.get(key, rd[key])
        blended[key] = _clamp(rd[key] * RULE_WEIGHT + ai_val * AI_WEIGHT)
    return PersonalityScores(**blended)


# ─── Main entry point ─────────────────────────────────────────────────────────

def analyze(
    conv: ParsedConversation,
    speaker: Optional[str] = None,
    progress_callback=None,
) -> AnalysisResult:
    """
    Run the full personality analysis pipeline.

    Args:
        conv: Parsed conversation from the parser module.
        speaker: Which speaker to analyse.  Defaults to ``conv.target_speaker``.
        progress_callback: Optional callable(step: str) for progress reporting.

    Returns:
        :class:`AnalysisResult` with all scores and insights populated.
    """
    speaker = speaker or conv.target_speaker
    stats = conv.stats.get(speaker)
    if stats is None:
        raise ValueError(f"Speaker '{speaker}' not found in conversation.")

    text = _extract_messages_text(conv, speaker)

    def _tick(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    _tick("Extracting text features …")
    topics = _analyze_topics(text.lower())

    _tick("Running sentiment analysis …")
    sentiment = _analyze_sentiment(text)

    _tick("Computing rule-based personality scores …")
    rule_scores = _rule_based_scores(text, stats)
    comm_style, behav_ind, think_style = _rule_based_styles(text, rule_scores)

    _tick("Querying AI model …")
    ai_insights_raw = _call_openai(speaker, text, stats)
    ai_available = ai_insights_raw is not None

    if not ai_available:
        ai_insights = _fallback_insights(speaker, rule_scores, stats)
    else:
        ai_insights = ai_insights_raw  # type: ignore

    _tick("Blending scores …")
    final_scores = _blend(rule_scores, ai_insights.ai_scores if ai_available else None)

    return AnalysisResult(
        speaker=speaker,
        scores=final_scores,
        communication_style=comm_style,
        behavior_indicators=behav_ind,
        thinking_style=think_style,
        topics=topics,
        sentiment=sentiment,
        ai_insights=ai_insights,
        stats=stats,
        ai_available=ai_available,
    )
