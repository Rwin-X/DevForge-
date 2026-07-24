"""
Chat Personality Analyzer - Report Generator
=============================================
Generates JSON, Markdown, and HTML reports from an AnalysisResult.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import APP_NAME, APP_VERSION, REPORTS_DIR
from parser import ParsedConversation
from personality_engine import AnalysisResult


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _score_label(score: float) -> str:
    if score >= 80:
        return "Very High"
    if score >= 65:
        return "High"
    if score >= 45:
        return "Moderate"
    if score >= 25:
        return "Low"
    return "Very Low"


def _bar(score: float, width: int = 20) -> str:
    """ASCII progress bar for markdown."""
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ─── JSON ──────────────────────────────────────────────────────────────────────

def generate_json(
    result: AnalysisResult,
    conv: ParsedConversation,
    output_path: Optional[Path] = None,
) -> Path:
    output_path = output_path or REPORTS_DIR / "report.json"
    data = {
        "meta": {
            "tool": APP_NAME,
            "version": APP_VERSION,
            "generated_at": _ts(),
            "subject": result.speaker,
            "chat_format": conv.format_detected,
            "ai_powered": result.ai_available,
        },
        "statistics": {
            "message_count": result.stats.message_count,
            "total_words": result.stats.total_words,
            "avg_message_length_words": round(result.stats.avg_message_length, 1),
            "avg_message_length_chars": round(result.stats.avg_char_length, 1),
            "questions_asked": result.stats.question_count,
            "exclamations": result.stats.exclamation_count,
            "emojis_used": result.stats.emoji_count,
            "avg_response_time_seconds": (
                round(result.stats.avg_response_time, 1)
                if result.stats.avg_response_time
                else None
            ),
            "all_speakers": conv.speakers,
            "total_conversation_messages": conv.total_messages,
        },
        "personality_scores": result.scores.as_dict(),
        "communication_style": {
            "formality": round(result.communication_style.formality, 1),
            "friendliness": round(result.communication_style.friendliness, 1),
            "assertiveness": round(result.communication_style.assertiveness, 1),
            "emotional_expression": round(result.communication_style.emotional_expression, 1),
            "humor_usage": round(result.communication_style.humor_usage, 1),
        },
        "behavior_indicators": {
            "curiosity": round(result.behavior_indicators.curiosity, 1),
            "confidence": round(result.behavior_indicators.confidence, 1),
            "patience": round(result.behavior_indicators.patience, 1),
            "leadership": round(result.behavior_indicators.leadership, 1),
            "independence": round(result.behavior_indicators.independence, 1),
            "openness": round(result.behavior_indicators.openness, 1),
        },
        "thinking_style": {
            "analytical": round(result.thinking_style.analytical, 1),
            "creative": round(result.thinking_style.creative, 1),
            "practical": round(result.thinking_style.practical, 1),
            "strategic": round(result.thinking_style.strategic, 1),
            "detail_oriented": round(result.thinking_style.detail_oriented, 1),
        },
        "topics": [
            {"topic": t.topic, "confidence": t.confidence, "mention_count": t.mention_count}
            for t in result.topics
        ],
        "sentiment": (
            {
                "overall_polarity": round(result.sentiment.overall_polarity, 3),
                "overall_subjectivity": round(result.sentiment.overall_subjectivity, 3),
                "positive_ratio": round(result.sentiment.positive_ratio, 3),
                "negative_ratio": round(result.sentiment.negative_ratio, 3),
                "neutral_ratio": round(result.sentiment.neutral_ratio, 3),
            }
            if result.sentiment
            else None
        ),
        "insights": {
            "executive_summary": result.ai_insights.executive_summary,
            "personality_summary": result.ai_insights.personality_summary,
            "communication_profile": result.ai_insights.communication_profile,
            "strengths": result.ai_insights.strengths,
            "weaknesses": result.ai_insights.weaknesses,
            "final_assessment": result.ai_insights.final_assessment,
        },
        "disclaimer": (
            "All scores are probabilistic estimates based on language patterns. "
            "They may indicate tendencies but should never be used to make definitive "
            "conclusions about a person's character."
        ),
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


# ─── Markdown ─────────────────────────────────────────────────────────────────

def generate_markdown(
    result: AnalysisResult,
    conv: ParsedConversation,
    output_path: Optional[Path] = None,
) -> Path:
    output_path = output_path or REPORTS_DIR / "report.md"
    sd = result.scores.as_dict()
    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}\n")

    def p(text: str) -> None:
        lines.append(f"{text}\n")

    def hr() -> None:
        lines.append("---\n")

    h(1, f"🧠 {APP_NAME} — Personality Report")
    p(f"**Subject:** {result.speaker}  ")
    p(f"**Generated:** {_ts()}  ")
    p(f"**Chat Format:** {conv.format_detected}  ")
    p(f"**AI-Powered:** {'Yes' if result.ai_available else 'No (rule-based only)'}  ")
    hr()

    # Executive Summary
    h(2, "📋 Executive Summary")
    p(f"> {result.ai_insights.executive_summary}")
    p("")
    p(result.ai_insights.personality_summary)
    hr()

    # Statistics
    h(2, "📊 Conversation Statistics")
    p(f"| Metric | Value |")
    p(f"|--------|-------|")
    p(f"| Messages from {result.speaker} | {result.stats.message_count} |")
    p(f"| Total conversation messages | {conv.total_messages} |")
    p(f"| Avg message length | {result.stats.avg_message_length:.1f} words |")
    p(f"| Questions asked | {result.stats.question_count} |")
    p(f"| Exclamations | {result.stats.exclamation_count} |")
    p(f"| Emojis used | {result.stats.emoji_count} |")
    if result.stats.avg_response_time:
        mins = result.stats.avg_response_time / 60
        p(f"| Avg response time | {mins:.1f} minutes |")
    p(f"| Total words | {result.stats.total_words:,} |")
    hr()

    # Personality Scores
    h(2, "🎯 Personality Scores")
    p(f"*Scores range 0–100.  All values are probabilistic estimates.*\n")
    for trait, score in sd.items():
        label = trait.replace("_", " ").title()
        bar = _bar(score)
        level = _score_label(score)
        p(f"**{label}** ({score:.0f}/100 — {level})")
        p(f"`{bar}`\n")
    hr()

    # Communication Style
    h(2, "💬 Communication Style")
    p(result.ai_insights.communication_profile)
    p("")
    p(f"| Dimension | Score | Level |")
    p(f"|-----------|-------|-------|")
    cs = result.communication_style
    for label, val in [
        ("Formality", cs.formality),
        ("Friendliness", cs.friendliness),
        ("Assertiveness", cs.assertiveness),
        ("Emotional Expression", cs.emotional_expression),
        ("Humor Usage", cs.humor_usage),
    ]:
        p(f"| {label} | {val:.0f} | {_score_label(val)} |")
    hr()

    # Behavior Indicators
    h(2, "🔍 Behavior Indicators")
    bi = result.behavior_indicators
    for label, val in [
        ("Curiosity", bi.curiosity),
        ("Confidence", bi.confidence),
        ("Patience", bi.patience),
        ("Leadership", bi.leadership),
        ("Independence", bi.independence),
        ("Openness", bi.openness),
    ]:
        p(f"- **{label}:** {val:.0f}/100 ({_score_label(val)})")
    hr()

    # Thinking Style
    h(2, "🧩 Thinking Style")
    ts = result.thinking_style
    for label, val in [
        ("Analytical", ts.analytical),
        ("Creative", ts.creative),
        ("Practical", ts.practical),
        ("Strategic", ts.strategic),
        ("Detail-Oriented", ts.detail_oriented),
    ]:
        p(f"- **{label}:** {val:.0f}/100 ({_score_label(val)})")
    hr()

    # Topics
    if result.topics:
        h(2, "📌 Detected Interests")
        for t in result.topics[:8]:
            bar = _bar(t.confidence, 15)
            p(f"- **{t.topic}** ({t.confidence:.0f}%) `{bar}` ({t.mention_count} mentions)")
    hr()

    # Sentiment
    if result.sentiment:
        h(2, "💭 Sentiment Profile")
        s = result.sentiment
        polarity_label = "Positive" if s.overall_polarity > 0.1 else ("Negative" if s.overall_polarity < -0.1 else "Neutral")
        p(f"- **Overall Tone:** {polarity_label} ({s.overall_polarity:+.2f})")
        p(f"- **Subjectivity:** {s.overall_subjectivity:.2f} ({'Opinionated' if s.overall_subjectivity > 0.5 else 'Objective'})")
        p(f"- **Positive messages:** {s.positive_ratio:.0%}")
        p(f"- **Negative messages:** {s.negative_ratio:.0%}")
        p(f"- **Neutral messages:** {s.neutral_ratio:.0%}")
        hr()

    # Strengths
    h(2, "✅ Strengths")
    for s in result.ai_insights.strengths:
        p(f"- {s}")
    hr()

    # Weaknesses
    h(2, "⚠️ Potential Areas for Growth")
    for w in result.ai_insights.weaknesses:
        p(f"- {w}")
    hr()

    # Final Assessment
    h(2, "🏁 Final Assessment")
    p(result.ai_insights.final_assessment)
    hr()

    # Disclaimer
    h(2, "⚖️ Disclaimer")
    p(
        "*All scores are probabilistic estimates derived from language patterns in chat messages. "
        "They may indicate tendencies but should never be used to make definitive conclusions "
        "about a person's character, intentions, or capabilities. This tool is for informational "
        "and entertainment purposes only.*"
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ─── HTML ─────────────────────────────────────────────────────────────────────

def generate_html(
    result: AnalysisResult,
    conv: ParsedConversation,
    output_path: Optional[Path] = None,
) -> Path:
    output_path = output_path or REPORTS_DIR / "report.html"
    sd = result.scores.as_dict()

    def _score_color(score: float) -> str:
        if score >= 80:
            return "#00D4AA"
        if score >= 60:
            return "#4ECDC4"
        if score >= 40:
            return "#FFE66D"
        if score >= 20:
            return "#FF6B6B"
        return "#C0392B"

    def _score_bar_html(score: float, label: str) -> str:
        color = _score_color(score)
        level = _score_label(score)
        return f"""
        <div class="score-item">
          <div class="score-header">
            <span class="score-label">{label}</span>
            <span class="score-value" style="color:{color}">{score:.0f}</span>
          </div>
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:{score}%;background:{color}"></div>
          </div>
          <div class="score-level">{level}</div>
        </div>"""

    scores_html = "".join(
        _score_bar_html(v, k.replace("_", " ").title())
        for k, v in sd.items()
    )

    topics_html = ""
    for t in result.topics[:6]:
        color = _score_color(t.confidence)
        topics_html += f"""
        <div class="topic-chip" style="border-color:{color};color:{color}">
          {t.topic} <span class="topic-score">{t.confidence:.0f}%</span>
        </div>"""

    strengths_html = "".join(
        f'<li class="insight-item strength-item">✅ {s}</li>'
        for s in result.ai_insights.strengths
    )
    weaknesses_html = "".join(
        f'<li class="insight-item weakness-item">⚠️ {w}</li>'
        for w in result.ai_insights.weaknesses
    )

    sentiment_html = ""
    if result.sentiment:
        s = result.sentiment
        pol_color = "#00D4AA" if s.overall_polarity > 0.1 else ("#FF6B6B" if s.overall_polarity < -0.1 else "#FFE66D")
        pol_label = "Positive" if s.overall_polarity > 0.1 else ("Negative" if s.overall_polarity < -0.1 else "Neutral")
        sentiment_html = f"""
        <div class="stat-card">
          <div class="stat-value" style="color:{pol_color}">{pol_label}</div>
          <div class="stat-label">Overall Tone ({s.overall_polarity:+.2f})</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{s.positive_ratio:.0%}</div>
          <div class="stat-label">Positive Messages</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{s.negative_ratio:.0%}</div>
          <div class="stat-label">Negative Messages</div>
        </div>"""

    rt_html = ""
    if result.stats.avg_response_time:
        mins = result.stats.avg_response_time / 60
        rt_html = f"""
        <div class="stat-card">
          <div class="stat-value">{mins:.1f}m</div>
          <div class="stat-label">Avg Response Time</div>
        </div>"""

    cs = result.communication_style
    bi = result.behavior_indicators
    ts_obj = result.thinking_style

    def _mini_bar(val: float, label: str) -> str:
        color = _score_color(val)
        return f"""
        <div class="mini-bar-row">
          <span class="mini-label">{label}</span>
          <div class="mini-bar-bg">
            <div class="mini-bar-fill" style="width:{val}%;background:{color}"></div>
          </div>
          <span class="mini-val">{val:.0f}</span>
        </div>"""

    comm_bars = "".join([
        _mini_bar(cs.formality, "Formality"),
        _mini_bar(cs.friendliness, "Friendliness"),
        _mini_bar(cs.assertiveness, "Assertiveness"),
        _mini_bar(cs.emotional_expression, "Emotional Expr."),
        _mini_bar(cs.humor_usage, "Humor Usage"),
    ])
    behav_bars = "".join([
        _mini_bar(bi.curiosity, "Curiosity"),
        _mini_bar(bi.confidence, "Confidence"),
        _mini_bar(bi.patience, "Patience"),
        _mini_bar(bi.leadership, "Leadership"),
        _mini_bar(bi.independence, "Independence"),
        _mini_bar(bi.openness, "Openness"),
    ])
    think_bars = "".join([
        _mini_bar(ts_obj.analytical, "Analytical"),
        _mini_bar(ts_obj.creative, "Creative"),
        _mini_bar(ts_obj.practical, "Practical"),
        _mini_bar(ts_obj.strategic, "Strategic"),
        _mini_bar(ts_obj.detail_oriented, "Detail-Oriented"),
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{APP_NAME} — {result.speaker}</title>
<style>
  :root {{
    --bg: #0D0F1A;
    --surface: #161929;
    --surface2: #1E2235;
    --border: #2A2E45;
    --accent: #00D4AA;
    --accent2: #7B61FF;
    --text: #E8EAF0;
    --text-muted: #7A7F9A;
    --radius: 12px;
    --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    --mono: 'Cascadia Code', 'Fira Code', monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 15px;
    line-height: 1.7;
    min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #0D0F1A 0%, #1a1030 50%, #0D0F1A 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 0 30px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 300px;
    background: radial-gradient(ellipse, rgba(0,212,170,0.08) 0%, transparent 70%);
    pointer-events: none;
  }}
  .header-badge {{
    display: inline-block;
    background: rgba(0,212,170,0.1);
    border: 1px solid rgba(0,212,170,0.3);
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 16px;
  }}
  .header h1 {{
    font-size: clamp(24px, 5vw, 42px);
    font-weight: 700;
    letter-spacing: -1px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}
  .header-meta {{
    color: var(--text-muted);
    font-size: 13px;
  }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 32px 20px; }}
  .section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px;
    margin-bottom: 24px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section-title::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}
  .exec-summary {{
    background: linear-gradient(135deg, var(--surface2), var(--surface));
    border-left: 3px solid var(--accent);
    padding: 20px 24px;
    border-radius: 0 var(--radius) var(--radius) 0;
    font-style: italic;
    color: var(--text);
    margin-bottom: 16px;
    font-size: 16px;
  }}
  .body-text {{ color: var(--text-muted); line-height: 1.8; }}
  /* Stats grid */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px;
    margin-bottom: 8px;
  }}
  .stat-card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }}
  .stat-value {{
    font-size: 28px;
    font-weight: 700;
    color: var(--accent);
    font-family: var(--mono);
    line-height: 1.2;
  }}
  .stat-label {{
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  /* Personality scores */
  .scores-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
  .score-item {{ margin-bottom: 4px; }}
  .score-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }}
  .score-label {{ font-size: 13px; font-weight: 600; color: var(--text); }}
  .score-value {{ font-size: 22px; font-weight: 700; font-family: var(--mono); }}
  .score-bar-bg {{ background: var(--border); border-radius: 4px; height: 6px; overflow: hidden; }}
  .score-bar-fill {{ height: 100%; border-radius: 4px; transition: width 1s ease; }}
  .score-level {{ font-size: 11px; color: var(--text-muted); margin-top: 3px; }}
  /* Mini bars */
  .mini-bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .mini-label {{ font-size: 12px; color: var(--text-muted); width: 110px; flex-shrink: 0; }}
  .mini-bar-bg {{ flex: 1; background: var(--border); border-radius: 3px; height: 5px; overflow: hidden; }}
  .mini-bar-fill {{ height: 100%; border-radius: 3px; }}
  .mini-val {{ font-size: 12px; color: var(--text-muted); width: 28px; text-align: right; font-family: var(--mono); }}
  /* Style sub-sections */
  .style-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px; }}
  .style-card {{ background: var(--surface2); border-radius: 10px; padding: 20px; }}
  .style-card-title {{ font-size: 12px; color: var(--accent); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 16px; }}
  /* Topics */
  .topics-wrap {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .topic-chip {{
    border: 1px solid;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .topic-score {{ opacity: 0.7; font-size: 11px; }}
  /* Insights */
  .insight-list {{ list-style: none; }}
  .insight-item {{ padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 14px; color: var(--text-muted); }}
  .insight-item:last-child {{ border-bottom: none; }}
  .strength-item {{ color: #7EFFA0; }}
  .weakness-item {{ color: #FFB86C; }}
  /* Two columns for strengths/weaknesses */
  .insights-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 600px) {{ .insights-grid {{ grid-template-columns: 1fr; }} }}
  /* Footer */
  .footer {{
    text-align: center;
    padding: 40px 20px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
    margin-top: 20px;
  }}
  .disclaimer {{
    background: rgba(255,184,108,0.05);
    border: 1px solid rgba(255,184,108,0.2);
    border-radius: var(--radius);
    padding: 16px 20px;
    font-size: 13px;
    color: #FFB86C;
    line-height: 1.6;
  }}
  .ai-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(123,97,255,0.1);
    border: 1px solid rgba(123,97,255,0.3);
    color: var(--accent2);
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
    vertical-align: middle;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-badge">Personality Report</div>
  <h1>🧠 {result.speaker}</h1>
  <div class="header-meta">
    Generated {_ts()} &nbsp;·&nbsp; {conv.format_detected} &nbsp;·&nbsp;
    {'<span class="ai-badge">⚡ AI-Powered</span>' if result.ai_available else '<span class="ai-badge" style="color:#7A7F9A;border-color:rgba(122,127,154,0.3)">Rule-Based</span>'}
  </div>
</div>

<div class="container">

  <!-- Executive Summary -->
  <div class="section">
    <div class="section-title">📋 Executive Summary</div>
    <div class="exec-summary">{result.ai_insights.executive_summary}</div>
    <div class="body-text">{result.ai_insights.personality_summary.replace(chr(10), '<br>')}</div>
  </div>

  <!-- Stats -->
  <div class="section">
    <div class="section-title">📊 Statistics</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{result.stats.message_count:,}</div>
        <div class="stat-label">Messages</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{result.stats.avg_message_length:.0f}</div>
        <div class="stat-label">Avg Words / Msg</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{result.stats.question_count}</div>
        <div class="stat-label">Questions Asked</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{result.stats.emoji_count}</div>
        <div class="stat-label">Emojis Used</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{result.stats.total_words:,}</div>
        <div class="stat-label">Total Words</div>
      </div>
      {rt_html}
      {sentiment_html}
    </div>
  </div>

  <!-- Personality Scores -->
  <div class="section">
    <div class="section-title">🎯 Personality Scores <span style="font-size:11px;color:var(--text-muted);text-transform:none;letter-spacing:0;font-weight:400">(0–100, probabilistic)</span></div>
    <div class="scores-grid">
      {scores_html}
    </div>
  </div>

  <!-- Style breakdown -->
  <div class="section">
    <div class="section-title">🔬 Detailed Analysis</div>
    <div class="style-grid">
      <div class="style-card">
        <div class="style-card-title">💬 Communication Style</div>
        {comm_bars}
      </div>
      <div class="style-card">
        <div class="style-card-title">🧭 Behavior Indicators</div>
        {behav_bars}
      </div>
      <div class="style-card">
        <div class="style-card-title">🧩 Thinking Style</div>
        {think_bars}
      </div>
    </div>
  </div>

  <!-- Communication Profile -->
  <div class="section">
    <div class="section-title">💬 Communication Profile</div>
    <div class="body-text">{result.ai_insights.communication_profile.replace(chr(10), '<br>')}</div>
  </div>

  <!-- Topics -->
  {"" if not result.topics else f'''
  <div class="section">
    <div class="section-title">📌 Detected Interests</div>
    <div class="topics-wrap">{topics_html}</div>
  </div>'''}

  <!-- Strengths & Weaknesses -->
  <div class="section">
    <div class="section-title">✅ Strengths &amp; ⚠️ Growth Areas</div>
    <div class="insights-grid">
      <div>
        <div style="font-size:12px;color:#7EFFA0;font-weight:600;letter-spacing:1px;margin-bottom:12px">STRENGTHS</div>
        <ul class="insight-list">{strengths_html}</ul>
      </div>
      <div>
        <div style="font-size:12px;color:#FFB86C;font-weight:600;letter-spacing:1px;margin-bottom:12px">AREAS FOR GROWTH</div>
        <ul class="insight-list">{weaknesses_html}</ul>
      </div>
    </div>
  </div>

  <!-- Final Assessment -->
  <div class="section">
    <div class="section-title">🏁 Final Assessment</div>
    <div class="body-text">{result.ai_insights.final_assessment.replace(chr(10), '<br>')}</div>
  </div>

  <!-- Disclaimer -->
  <div class="disclaimer">
    ⚖️ <strong>Disclaimer:</strong> All scores and assessments are probabilistic estimates based on
    language patterns in chat messages. They <em>may indicate</em> tendencies but should never be used
    to make definitive conclusions about a person's character, intentions, or capabilities. This report
    is for informational and reflective purposes only.
  </div>

</div>

<div class="footer">
  Generated by {APP_NAME} v{APP_VERSION} &nbsp;·&nbsp; All data processed locally &nbsp;·&nbsp; No conversation data stored
</div>

</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path


# ─── Convenience wrapper ───────────────────────────────────────────────────────

def generate_all(
    result: AnalysisResult,
    conv: ParsedConversation,
    base_name: str = "report",
) -> dict[str, Path]:
    """Generate JSON, MD, and HTML reports. Returns dict of format → path."""
    paths = {
        "json": generate_json(result, conv, REPORTS_DIR / f"{base_name}.json"),
        "markdown": generate_markdown(result, conv, REPORTS_DIR / f"{base_name}.md"),
        "html": generate_html(result, conv, REPORTS_DIR / f"{base_name}.html"),
    }
    return paths
