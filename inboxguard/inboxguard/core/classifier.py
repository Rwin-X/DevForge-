"""Heuristic scoring of advertisements and AI-written emails.

Both scores are in [0, 1] and come with human-readable reasons.

Advertisement scoring is reliable because bulk mail carries structural
evidence (List-Unsubscribe, bulk headers, tracking pixels, promotional
wording).

AI-written text has no reliable detector. This module scores two kinds of
evidence: hard signals (pasted assistant boilerplate, unfilled template
placeholders) and soft stylistic signals. Soft signals alone are capped
below the default delete threshold, so they route mail to review instead
of deletion.
"""
from __future__ import annotations

import re
import statistics

from .models import ClassifierResult, ParsedEmail

# --------------------------------------------------------------------------
# Advertisement signals
# --------------------------------------------------------------------------

_BULK_HEADERS = (
    "x-mailchimp-id",
    "x-mc-user",
    "x-campaign",
    "x-campaignid",
    "x-mailgun-sid",
    "x-sg-eid",
    "x-sg-id",
    "x-ses-outgoing",
    "x-mandrill-user",
    "x-mailjet-campaign",
    "x-csa-complaints",
)
_BULK_MAILERS = re.compile(
    r"mailchimp|sendgrid|mailgun|sendinblue|brevo|constant contact|campaign monitor|"
    r"klaviyo|hubspot|marketo|mandrill|mailjet|amazon ses|salesforce|iterable",
    re.I,
)
_MARKETING_LOCALPART = re.compile(
    r"^(newsletters?|marketing|promo(tion)?s?|deals?|offers?|specials?|campaigns?|"
    r"mailer|digest|weekly|daily|shop|store)([._+-]|$)",
    re.I,
)
_SENDING_SUBDOMAIN = re.compile(
    r"^(e|em|email|mail|news|mg|send|info|marketing|click|go|t|m)\.", re.I
)
_SUBJECT_PROMO = re.compile(
    r"\b\d{1,2}\s?%\s?off\b|\bsale\b|limited[- ]time|last chance|\bexclusive\b|"
    r"free shipping|\bdeals?\b|discount|coupon|promo code|save up to|don'?t miss|"
    r"flash sale|black friday|cyber monday|buy one get one|special offer|act now|"
    r"clearance|\bnew arrivals?\b|\bbest sellers?\b|ends (tonight|today|soon)",
    re.I,
)
_BODY_PROMO = re.compile(
    r"shop now|buy now|order now|limited[- ]time offer|while supplies last|"
    r"terms and conditions apply|view (this email )?in (your )?browser|"
    r"manage (your )?(email )?preferences|update (your )?(email )?preferences|"
    r"you are receiving this (email|message) because|"
    r"you(?:'| a)?re? (?:are )?(?:receiving|got) this (?:email|message) (?:because|as)|"
    r"no longer wish to receive|\d{1,2}\s?%\s?off|free shipping|use code|promo code|"
    r"unsubscribe from (this|these)|add us to your address book",
    re.I,
)
_UNSUBSCRIBE_TEXT = re.compile(r"\bunsubscribe\b", re.I)
_TRANSACTIONAL = re.compile(
    r"verification code|security code|one[- ]time (code|password)|login code|sign[- ]in|"
    r"password reset|reset your password|security alert|order confirmation|"
    r"your (order|receipt|invoice|payment|booking|reservation|ticket)|"
    r"shipping confirmation|has shipped|delivery (update|notification)|"
    r"two[- ]factor|2fa|confirm your (email|account)",
    re.I,
)


def _noisy_or(weights: list[float]) -> float:
    remaining = 1.0
    for weight in weights:
        remaining *= 1.0 - max(0.0, min(1.0, weight))
    return 1.0 - remaining


def score_ad(mail: ParsedEmail) -> tuple[float, list[str]]:
    weights: list[float] = []
    reasons: list[str] = []

    def add(weight: float, reason: str) -> None:
        weights.append(weight)
        reasons.append(reason)

    headers = mail.headers
    if "list-unsubscribe" in headers:
        add(0.55, "List-Unsubscribe header present")
    precedence = headers.get("precedence", "").lower()
    if precedence in ("bulk", "list", "junk"):
        add(0.30, f"Precedence: {precedence}")
    if "list-id" in headers:
        add(0.20, "Mailing list (List-Id header)")
    if any(name in headers for name in _BULK_HEADERS):
        add(0.25, "Bulk-mailer tracking header")
    elif _BULK_MAILERS.search(headers.get("x-mailer", "")):
        add(0.25, "Sent through a bulk-mail platform")
    if "feedback-id" in headers:
        add(0.12, "Feedback-ID header (bulk sender)")

    address = mail.sender_address
    local, _, domain = address.partition("@")
    if _MARKETING_LOCALPART.match(local):
        add(0.40, f"Marketing-style sender address ({local})")
    elif local in ("noreply", "no-reply", "donotreply", "do-not-reply"):
        add(0.08, "No-reply sender")
    if _SENDING_SUBDOMAIN.match(domain):
        add(0.12, "Bulk-sending subdomain")

    subject_hits = {m.group(0).lower() for m in _SUBJECT_PROMO.finditer(mail.subject)}
    if subject_hits:
        weight = min(0.60, 0.30 + 0.12 * (len(subject_hits) - 1))
        add(weight, "Promotional subject: " + ", ".join(sorted(subject_hits)[:3]))
    letters = [c for c in mail.subject if c.isalpha()]
    if len(letters) >= 8 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        add(0.12, "Subject is mostly capital letters")
    if mail.subject.count("!") >= 2:
        add(0.08, "Multiple exclamation marks in subject")

    body = mail.text
    if _UNSUBSCRIBE_TEXT.search(body):
        add(0.25, "Body contains an unsubscribe link or text")
    body_hits = {m.group(0).lower() for m in _BODY_PROMO.finditer(body)}
    if body_hits:
        add(min(0.50, 0.14 * len(body_hits)), "Promotional wording in body")

    if mail.link_count >= 10:
        add(0.15, f"Many links ({mail.link_count})")
    if mail.image_count >= 4:
        add(0.10, f"Many images ({mail.image_count})")
    if mail.tracking_pixels:
        add(0.18, "Tracking pixel (1x1 image)")
    if mail.has_html and len(body.split()) < 40 and mail.image_count >= 2:
        add(0.10, "Image-heavy message with little text")

    score = _noisy_or(weights)
    if _TRANSACTIONAL.search(mail.subject + " " + body[:600]):
        if score > 0:
            reasons.append("Looks transactional (score reduced)")
        score *= 0.45
    return round(score, 3), reasons


# --------------------------------------------------------------------------
# AI-written text signals
# --------------------------------------------------------------------------

_AI_BOILERPLATE = re.compile(
    r"\bas an ai (?:language )?(?:model|assistant)\b|\bas a large language model\b|"
    r"\bi(?:'m| am) (?:just )?an ai\b|\bregenerate response\b|"
    r"\b(?:certainly|sure|absolutely)[!,.]? here(?:'s| is)\b|"
    r"\bhere(?:'s| is) (?:a|the|your) (?:draft|revised|polished|professional|improved)\b",
    re.I,
)
_PLACEHOLDER = re.compile(
    r"\[(?:your|recipient|insert|company|name|first name|last name|date|title|position|"
    r"sender|client|customer)\b[^\]\n]{0,40}\]",
    re.I,
)
_STOCK_PHRASES = re.compile(
    r"\b(?:i hope this (?:email|message) finds you well|i trust this (?:email|message) finds you well|"
    r"delve(?:s|d)? (?:into|deeper)|delve|tapestry|in today's (?:fast-paced|digital|ever-changing)|"
    r"ever-evolving landscape|it(?:'s| is) (?:important|worth) (?:to note|noting)|"
    r"navigate the complexities|unlock the (?:full )?potential|a testament to|game-changer|"
    r"i wanted to reach out|please (?:don't|do not) hesitate to reach out|"
    r"please feel free to reach out|i would be delighted to|"
    r"look forward to the opportunity to|i'd be happy to assist|rest assured)\b",
    re.I,
)
_BUZZWORDS = re.compile(
    r"\b(?:seamless(?:ly)?|leverag(?:e|ing)|robust|streamlin(?:e|ing)|elevate|cutting-edge|"
    r"holistic|synergy|pivotal|intricate|meticulous(?:ly)?|multifaceted|plethora|paramount|"
    r"foster(?:ing)?|embark(?:ing)?|realm|beacon|underscor(?:e|es|ing)|commendable|harness(?:ing)?)\b",
    re.I,
)
_TRANSITIONS = re.compile(r"\b(?:moreover|furthermore|additionally|consequently)\b", re.I)
_MARKDOWN_BOLD = re.compile(r"\*\*[^*\n]{2,60}\*\*")
_MARKDOWN_HEAD = re.compile(r"^\s{0,3}#{1,4}\s+\S", re.M)
_SUBJECT_LINE_FIRST = re.compile(r"\A\s*subject:\s", re.I)
_QUOTE_CUTOFF = re.compile(
    r"^(?:on .{5,120} wrote:|-{2,}\s*original message\s*-{2,}|from:\s.+\ssent:\s)", re.I | re.M
)


def _own_text(text: str) -> str:
    """Drop quoted replies so only the sender's own writing is scored."""
    cut = _QUOTE_CUTOFF.search(text)
    if cut:
        text = text[: cut.start()]
    lines = [line for line in text.splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(lines).strip()


def score_ai(mail: ParsedEmail) -> tuple[float, list[str]]:
    text = _own_text(mail.text).replace("\u2019", "'")
    reasons: list[str] = []
    hard: list[float] = []
    soft: list[float] = []

    if _AI_BOILERPLATE.search(text):
        hard.append(0.97)
        reasons.append("Contains AI assistant boilerplate")
    placeholders = {m.group(0) for m in _PLACEHOLDER.finditer(text)}
    if placeholders:
        hard.append(0.88)
        reasons.append("Unfilled template placeholder: " + ", ".join(sorted(placeholders)[:2]))

    words = text.split()
    if len(words) >= 25:
        stock = {m.group(0).lower() for m in _STOCK_PHRASES.finditer(text)}
        if stock:
            soft.append(min(0.60, 0.16 * len(stock)))
            reasons.append("Stock phrases: " + ", ".join(sorted(stock)[:3]))
        buzz = {m.group(0).lower() for m in _BUZZWORDS.finditer(text)}
        if buzz:
            soft.append(min(0.25, 0.07 * len(buzz)))
            reasons.append("Buzzwords: " + ", ".join(sorted(buzz)[:4]))
        if len(_TRANSITIONS.findall(text)) >= 3:
            soft.append(0.10)
            reasons.append("Heavy use of formal transition words")
        if _SUBJECT_LINE_FIRST.search(text):
            soft.append(0.50)
            reasons.append("Body starts with a pasted 'Subject:' line")
        if len(_MARKDOWN_BOLD.findall(text)) >= 2 or _MARKDOWN_HEAD.search(text):
            soft.append(0.25)
            reasons.append("Markdown formatting inside plain text")

    if len(words) >= 80:
        dashes = text.count("\u2014")
        if dashes / len(words) * 100 > 1.0:
            soft.append(0.10)
            reasons.append("High em-dash density")
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 3]
        if len(sentences) >= 6:
            lengths = [len(s.split()) for s in sentences]
            mean = statistics.fmean(lengths)
            if mean > 0 and statistics.pstdev(lengths) / mean < 0.30:
                soft.append(0.15)
                reasons.append("Unusually uniform sentence length")

    soft_score = min(0.85, _noisy_or(soft))
    score = _noisy_or(hard + [soft_score]) if hard else soft_score
    return round(score, 3), reasons


def classify(mail: ParsedEmail) -> ClassifierResult:
    ad_score, ad_reasons = score_ad(mail)
    ai_score, ai_reasons = score_ai(mail)
    return ClassifierResult(ad_score, ai_score, ad_reasons, ai_reasons)
