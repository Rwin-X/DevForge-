"""
ai_helper.py

A small, fully local "AI" helper. There is no model download, no API call,
and no network access anywhere in this file -- everything here is plain
text-processing that runs instantly on-device. It intentionally does only
three things:

  1. summarize_note   -> a short extractive summary
  2. suggest_tags     -> a handful of keyword-based tags
  3. suggest_related   -> other notes in the vault with similar content

This keeps the app honest about being "offline-only": there is nothing
here that could quietly reach out to a server.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from note_store import Note, NoteStore, WIKILINK_PATTERN

# A short, generic stopword list -- enough to keep tag/keyword output
# useful without pulling in a large external wordlist.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "so",
    "of", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above",
    "below", "to", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "once", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "should", "could", "can", "may", "might", "must",
    "shall", "this", "that", "these", "those", "i", "you", "he", "she",
    "it", "we", "they", "them", "his", "her", "its", "our", "their",
    "what", "which", "who", "whom", "as", "not", "no", "nor", "too",
    "very", "just", "also", "there", "here", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "s", "t", "don", "now",
}

WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]{1,}")


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax noise so text analysis sees plain prose."""
    text = WIKILINK_PATTERN.sub(lambda m: m.group(1), text)  # [[Link]] -> Link
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # code blocks
    text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [text](url)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"[*_>#-]", " ", text)  # leftover markdown symbols
    return text


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    # Simple sentence splitter -- good enough for personal notes without
    # pulling in an NLP dependency.
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 0]


def _word_tokens(text: str) -> list[str]:
    return [w.lower() for w in WORD_PATTERN.findall(text)]


# ---------------------------------------------------------------------- #
# 1. Summarize
# ---------------------------------------------------------------------- #

def summarize_note(note: Note, max_sentences: int = 3) -> str:
    """
    Extractive summary: scores each sentence by frequency of its
    significant words, then returns the highest-scoring sentences in
    their original order.
    """
    plain = _strip_markdown(note.content)
    sentences = _split_sentences(plain)

    if not sentences:
        return "(Note is empty -- nothing to summarize yet.)"
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    word_freq = Counter()
    for sentence in sentences:
        for word in _word_tokens(sentence):
            if word not in STOPWORDS and len(word) > 2:
                word_freq[word] += 1

    if not word_freq:
        return " ".join(sentences[:max_sentences])

    max_freq = max(word_freq.values())
    scores = []
    for idx, sentence in enumerate(sentences):
        words = [w for w in _word_tokens(sentence) if w not in STOPWORDS]
        if not words:
            score = 0.0
        else:
            score = sum(word_freq.get(w, 0) for w in words) / max_freq / len(words) ** 0.5
        # Small boost for early sentences (titles/intros tend to matter more)
        position_boost = 1.15 if idx == 0 else 1.0
        scores.append((score * position_boost, idx, sentence))

    top = sorted(scores, key=lambda x: x[0], reverse=True)[:max_sentences]
    top_in_order = [s for _, _, s in sorted(top, key=lambda x: x[1])]
    return " ".join(top_in_order)


# ---------------------------------------------------------------------- #
# 2. Suggest tags
# ---------------------------------------------------------------------- #

def suggest_tags(note: Note, all_notes: list[Note], max_tags: int = 6) -> list[str]:
    """
    Keyword extraction using TF-IDF against the rest of the vault, so
    tags favor words that are distinctive to this note rather than
    common across everything (e.g. "note", "today").
    """
    plain = _strip_markdown(note.content) + " " + note.note_id
    this_words = [w for w in _word_tokens(plain) if w not in STOPWORDS and len(w) > 2]

    if not this_words:
        return []

    tf = Counter(this_words)

    # Document frequency across the vault (how many other notes use each word)
    doc_count = max(len(all_notes), 1)
    df = Counter()
    for other in all_notes:
        other_words = set(
            w for w in _word_tokens(_strip_markdown(other.content) + " " + other.note_id)
            if w not in STOPWORDS and len(w) > 2
        )
        for w in other_words:
            df[w] += 1

    scores = {}
    for word, freq in tf.items():
        idf = math.log((doc_count + 1) / (df.get(word, 0) + 1)) + 1
        scores[word] = freq * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in ranked[:max_tags]]


# ---------------------------------------------------------------------- #
# 3. Suggest related notes
# ---------------------------------------------------------------------- #

def suggest_related(note: Note, store: NoteStore, max_results: int = 5) -> list[tuple[str, float]]:
    """
    Ranks other notes by content similarity (Jaccard over significant
    words) plus a bonus for notes that already share a wiki link, so
    linked notes and thematically similar notes both surface.
    """
    this_words = set(
        w for w in _word_tokens(_strip_markdown(note.content)) if w not in STOPWORDS and len(w) > 2
    )
    linked_ids = set(note.links_out) | set(note.links_in)

    results = []
    for other in store.all_notes():
        if other.note_id == note.note_id:
            continue
        other_words = set(
            w for w in _word_tokens(_strip_markdown(other.content))
            if w not in STOPWORDS and len(w) > 2
        )
        if not this_words and not other_words:
            similarity = 0.0
        else:
            union = this_words | other_words
            intersection = this_words & other_words
            similarity = len(intersection) / len(union) if union else 0.0

        if other.note_id in linked_ids:
            similarity += 0.15  # small nudge so already-linked notes rank fairly

        if similarity > 0:
            results.append((other.note_id, round(min(similarity, 1.0), 3)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:max_results]
