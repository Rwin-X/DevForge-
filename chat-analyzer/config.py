"""
Chat Personality Analyzer - Configuration Module
================================================
Central configuration for all analyzer components.
"""

import os
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"

REPORTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ─── OpenAI / LLM ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"   # swap to "gpt-4o" for higher quality
MAX_TOKENS = 2000
TEMPERATURE = 0.7

# Context window: how many chars of messages we send to the LLM
LLM_CONTEXT_CHARS = 8000

# ─── Analysis ─────────────────────────────────────────────────────────────────
MIN_MESSAGES_FOR_ANALYSIS = 5   # warn if fewer than this

# Personality trait score weights (rule-based → AI blend)
RULE_WEIGHT = 0.55
AI_WEIGHT = 0.45

# ─── Topics ───────────────────────────────────────────────────────────────────
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Technology": [
        "tech", "software", "hardware", "computer", "laptop", "server",
        "cloud", "api", "code", "programming", "developer", "engineer",
        "startup", "app", "mobile", "web", "internet", "network", "ai",
        "machine learning", "artificial intelligence", "robot", "automation",
    ],
    "Programming": [
        "python", "javascript", "typescript", "rust", "golang", "java", "c++",
        "c#", "ruby", "php", "sql", "html", "css", "react", "vue", "angular",
        "django", "flask", "fastapi", "github", "git", "docker", "kubernetes",
        "algorithm", "data structure", "function", "class", "object", "loop",
        "debug", "refactor", "pull request", "merge", "deploy",
    ],
    "Cybersecurity": [
        "security", "hack", "exploit", "vulnerability", "ctf", "pentest",
        "malware", "phishing", "firewall", "vpn", "encryption", "cipher",
        "zero-day", "reverse engineering", "forensics", "osint", "kali",
        "metasploit", "burp suite", "nmap", "wireshark", "payload",
    ],
    "Gaming": [
        "game", "gaming", "gamer", "play", "steam", "console", "xbox",
        "playstation", "nintendo", "fps", "rpg", "mmorpg", "esports",
        "twitch", "minecraft", "valorant", "fortnite", "league of legends",
        "overwatch", "raid", "quest", "level", "character", "spawn",
    ],
    "Business": [
        "business", "startup", "entrepreneur", "investor", "venture capital",
        "revenue", "profit", "market", "strategy", "ceo", "founder",
        "product", "sales", "customer", "client", "b2b", "saas", "pivot",
        "scale", "growth hacking", "kpi", "roadmap", "pitch deck",
    ],
    "Finance": [
        "money", "invest", "stock", "crypto", "bitcoin", "ethereum",
        "finance", "budget", "savings", "portfolio", "dividend", "bond",
        "etf", "forex", "trading", "defi", "nft", "inflation", "interest",
        "economy", "wealth", "passive income", "fire", "401k",
    ],
    "Science": [
        "science", "physics", "chemistry", "biology", "astronomy", "math",
        "research", "experiment", "theory", "hypothesis", "data", "study",
        "paper", "journal", "nature", "space", "quantum", "relativity",
        "evolution", "dna", "neuroscience", "climate", "environment",
    ],
    "Movies & TV": [
        "movie", "film", "cinema", "watch", "series", "netflix", "hbo",
        "disney", "marvel", "dc", "director", "actor", "actress", "oscar",
        "episode", "season", "trailer", "plot", "character", "streaming",
        "screenplay", "animation", "documentary",
    ],
    "Books": [
        "book", "read", "novel", "author", "fiction", "nonfiction", "library",
        "literature", "chapter", "kindle", "ebook", "audiobook", "biography",
        "memoir", "plot", "protagonist", "genre", "bestseller", "goodreads",
    ],
    "Fitness": [
        "gym", "workout", "exercise", "fitness", "run", "lift", "protein",
        "diet", "nutrition", "calories", "weight", "muscle", "cardio",
        "yoga", "meditation", "crossfit", "marathon", "personal trainer",
        "supplement", "sleep", "recovery", "health",
    ],
    "Travel": [
        "travel", "trip", "flight", "hotel", "country", "city", "explore",
        "adventure", "backpack", "visa", "passport", "culture", "food",
        "tourist", "vacation", "holiday", "airbnb", "itinerary", "jet lag",
        "hostel", "destination",
    ],
    "Relationships": [
        "friend", "family", "relationship", "partner", "love", "date",
        "marriage", "social", "people", "communication", "trust", "support",
        "conflict", "emotion", "empathy", "connection", "bond", "breakup",
        "advice", "feelings",
    ],
}

# ─── Personality Trait Signals ─────────────────────────────────────────────────
CURIOSITY_SIGNALS = [
    "?", "how", "why", "what if", "wonder", "curious", "interesting",
    "tell me", "explain", "learn", "understand", "discover", "explore",
]
HUMOR_SIGNALS = [
    "haha", "lol", "lmao", "😂", "🤣", "😆", "funny", "joke", "hehe",
    "rofl", "😄", "hilarious", "cringe", "bruh", "💀",
]
ASSERTIVE_SIGNALS = [
    "definitely", "absolutely", "clearly", "obviously", "must", "should",
    "need to", "have to", "no doubt", "certain", "sure", "of course",
]
EMPATHY_SIGNALS = [
    "feel", "understand", "sorry", "hope", "care", "support", "there for",
    "listen", "relate", "tough", "hard", "miss", "❤️", "💙", "🙏",
]
ANALYTICAL_SIGNALS = [
    "because", "therefore", "analysis", "data", "evidence", "logic",
    "reason", "conclude", "argument", "compare", "evaluate", "consider",
    "systematic", "structured", "hypothesis",
]
CREATIVITY_SIGNALS = [
    "imagine", "create", "design", "idea", "concept", "vision", "build",
    "innovate", "original", "unique", "art", "inspire", "dream", "invent",
]
LEADERSHIP_SIGNALS = [
    "let's", "we should", "i think we", "plan", "organize", "lead",
    "decision", "team", "coordinate", "strategy", "goal", "direction",
    "manage", "guide", "initiative",
]

# ─── Formality Word Lists ──────────────────────────────────────────────────────
INFORMAL_MARKERS = [
    "gonna", "wanna", "gotta", "kinda", "sorta", "ya", "yea", "yeah",
    "nope", "nah", "dunno", "tbh", "imo", "imho", "btw", "idk", "omg",
    "wtf", "lol", "haha", "bruh", "dude", "bro", "fam",
]
FORMAL_MARKERS = [
    "therefore", "furthermore", "additionally", "consequently", "regarding",
    "appreciate", "sincerely", "respectfully", "acknowledge", "request",
    "assist", "provide", "ensure", "utilize", "facilitate",
]

# ─── Display ───────────────────────────────────────────────────────────────────
APP_NAME = "Chat Personality Analyzer"
APP_VERSION = "1.0.0"
ACCENT_COLOR = "#00D4AA"
