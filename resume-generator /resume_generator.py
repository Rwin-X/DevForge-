#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║           RESUME.GEN  //  Hacker Portfolio Builder            ║
║           Pure Python · No dependencies · Claude API          ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
  python resume_gen.py                        # interactive wizard
  python resume_gen.py --name "Alex" --title "Pentester" --skills "Python,Nmap"
  python resume_gen.py --config resume.json   # load from JSON file
  python resume_gen.py --help
"""

import argparse
import json
import os
import re
import sys
import time
import textwrap
import urllib.request
import urllib.error
from datetime import datetime

# ══════════════════════════════════════════════════════════════
#  ANSI COLOR SYSTEM
# ══════════════════════════════════════════════════════════════

class C:
    """ANSI color codes — the terminal is the canvas."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"
    UNDER   = "\033[4m"
    BLINK   = "\033[5m"

    # Foreground
    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    # Bright foreground
    BCYAN   = "\033[96m"
    BGREEN  = "\033[92m"
    BRED    = "\033[91m"
    BWHITE  = "\033[97m"
    BBLUE   = "\033[94m"
    BMAGENTA= "\033[95m"
    BYELLOW = "\033[93m"

    # Background
    BG_BLACK  = "\033[40m"
    BG_CYAN   = "\033[46m"
    BG_BLUE   = "\033[44m"

def c(text, *codes):
    return "".join(codes) + str(text) + C.RESET

def cprint(text, *codes, end="\n"):
    print("".join(codes) + str(text) + C.RESET, end=end)


# ══════════════════════════════════════════════════════════════
#  TERMINAL UTILITIES
# ══════════════════════════════════════════════════════════════

def term_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def hr(char="─", color=C.DIM):
    w = min(term_width(), 80)
    print(color + char * w + C.RESET)

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def typewrite(text, delay=0.018, color=C.BCYAN):
    """CRT typewriter effect."""
    for ch in text:
        sys.stdout.write(color + ch + C.RESET)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def glitch_print(text, color=C.BCYAN, glitch_char="█"):
    """Glitch-reveal animation for headers."""
    w = len(text)
    import random
    for i in range(w + 1):
        revealed = text[:i]
        remaining = glitch_char * min(3, w - i)
        sys.stdout.write(
            "\r" + color + C.BOLD + revealed + C.RESET +
            c(remaining, C.DIM, C.GREEN) + "   "
        )
        sys.stdout.flush()
        time.sleep(0.03)
    sys.stdout.write("\r" + color + C.BOLD + text + C.RESET + "\n")
    sys.stdout.flush()

def spinner(msg, duration=1.5):
    """Neon spinner for waiting states."""
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    colors = [C.BCYAN, C.BMAGENTA, C.BBLUE, C.BCYAN]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        frame = frames[i % len(frames)]
        col = colors[i % len(colors)]
        sys.stdout.write(f"\r{col}{frame}{C.RESET} {c(msg, C.DIM)}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * (len(msg) + 6) + "\r")
    sys.stdout.flush()

def progress_bar(label, width=40, char_done="▓", char_empty="░", color=C.BCYAN):
    """Animated fill progress bar."""
    print(f"  {c(label, C.DIM)}")
    sys.stdout.write("  " + c("[", C.DIM))
    for i in range(width):
        time.sleep(0.015)
        sys.stdout.write(color + char_done + C.RESET)
        sys.stdout.flush()
    print(c("]", C.DIM) + " " + c("100%", C.BGREEN))


# ══════════════════════════════════════════════════════════════
#  BOOT SEQUENCE
# ══════════════════════════════════════════════════════════════

BANNER = r"""
 ██████╗ ███████╗███████╗██╗   ██╗███╗   ███╗███████╗
 ██╔══██╗██╔════╝██╔════╝██║   ██║████╗ ████║██╔════╝
 ██████╔╝█████╗  ███████╗██║   ██║██╔████╔██║█████╗  
 ██╔══██╗██╔══╝  ╚════██║██║   ██║██║╚██╔╝██║██╔══╝  
 ██║  ██║███████╗███████║╚██████╔╝██║ ╚═╝ ██║███████╗
 ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝
"""

BANNER2 = r"""
   ██████╗ ███████╗███╗   ██╗
  ██╔════╝ ██╔════╝████╗  ██║
  ██║  ███╗█████╗  ██╔██╗ ██║
  ██║   ██║██╔══╝  ██║╚██╗██║
  ╚██████╔╝███████╗██║ ╚████║
   ╚═════╝ ╚══════╝╚═╝  ╚═══╝
"""

def boot_sequence():
    clear()
    # Print banner with cyan glow effect
    for line in BANNER.split("\n"):
        cprint(line, C.BCYAN, C.BOLD)
        time.sleep(0.04)
    for line in BANNER2.split("\n"):
        cprint(line, C.BMAGENTA, C.BOLD)
        time.sleep(0.04)

    hr("═", C.BCYAN)
    cprint("  // AI-POWERED HACKER PORTFOLIO GENERATOR  ", C.DIM)
    cprint(f"  // claude-sonnet-4-6 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ", C.DIM)
    hr("═", C.BCYAN)
    print()

    boot_steps = [
        ("LOADING CORE MODULES      ", C.BCYAN),
        ("INITIALIZING CLAUDE API   ", C.BMAGENTA),
        ("CALIBRATING NEON RENDERER ", C.BBLUE),
        ("MOUNTING HTML FORGE       ", C.BGREEN),
        ("SYSTEM READY              ", C.BGREEN),
    ]
    for step, col in boot_steps:
        sys.stdout.write(f"  {c('▸', col)} {c(step, C.DIM)} ")
        sys.stdout.flush()
        time.sleep(0.12)
        cprint("[ OK ]", C.BGREEN, C.BOLD)
    print()


# ══════════════════════════════════════════════════════════════
#  ARGUMENT PARSER
# ══════════════════════════════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(
        prog="resume_gen.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
        ╔══════════════════════════════════════════════╗
        ║   RESUME.GEN — Hacker Portfolio CLI Tool     ║
        ╚══════════════════════════════════════════════╝

        Generates a complete cyberpunk dark-mode portfolio
        website as a single self-contained HTML file.
        Uses Claude AI to fill in any missing content.
        """),
        epilog=textwrap.dedent("""
        EXAMPLES:
          # Interactive wizard (recommended first run):
          python resume_gen.py

          # Minimal — AI generates the rest:
          python resume_gen.py --name "Alex Mercer" --title "Pentester" --skills "Python,Nmap,Wireshark"

          # Full spec:
          python resume_gen.py \\
            --name "Alex Mercer" \\
            --title "Senior Security Engineer" \\
            --email "alex@mercer.dev" \\
            --location "San Francisco, CA" \\
            --skills "Python,Bash,Nmap,Wireshark,Metasploit,Burp Suite" \\
            --github "https://github.com/alexmercer" \\
            --linkedin "https://linkedin.com/in/alexmercer" \\
            --about "Security researcher specializing in red team ops." \\
            --output my_portfolio.html

          # Load from JSON config:
          python resume_gen.py --config resume.json

          # Export JSON template to fill in:
          python resume_gen.py --export-template
        """)
    )

    # Identity
    g = p.add_argument_group("IDENTITY")
    g.add_argument("--name",     metavar="NAME",  help="Full name  (e.g. 'Alex Mercer')")
    g.add_argument("--title",    metavar="TITLE", help="Job title  (e.g. 'Senior Pentester')")
    g.add_argument("--email",    metavar="EMAIL", help="Contact email")
    g.add_argument("--location", metavar="LOC",   help="City, Country")
    g.add_argument("--about",    metavar="TEXT",  help="Bio / summary (AI generates if omitted)")

    # Links
    g2 = p.add_argument_group("LINKS")
    g2.add_argument("--github",    metavar="URL", help="GitHub profile URL")
    g2.add_argument("--linkedin",  metavar="URL", help="LinkedIn profile URL")
    g2.add_argument("--portfolio", metavar="URL", help="Personal website URL")
    g2.add_argument("--twitter",   metavar="URL", help="Twitter/X profile URL")

    # Skills
    g3 = p.add_argument_group("SKILLS")
    g3.add_argument("--skills", metavar="LIST",
                    help="Comma-separated skills (e.g. 'Python,Nmap,Wireshark')")

    # Structured data (JSON strings or files)
    g4 = p.add_argument_group("STRUCTURED DATA (JSON strings)")
    g4.add_argument("--experience", metavar="JSON",
                    help='JSON array: \'[{"title":"...","company":"...","start":"...","end":"...","desc":"..."}]\'')
    g4.add_argument("--education", metavar="JSON",
                    help='JSON array: \'[{"degree":"...","institution":"...","year":"...","gpa":"..."}]\'')
    g4.add_argument("--projects", metavar="JSON",
                    help='JSON array: \'[{"name":"...","tech":"...","desc":"...","url":"..."}]\'')
    g4.add_argument("--certifications", metavar="JSON",
                    help='JSON array: \'[{"name":"...","issuer":"...","year":"...","id":"..."}]\'')

    # Config & output
    g5 = p.add_argument_group("CONFIG & OUTPUT")
    g5.add_argument("--config",          metavar="FILE", help="Load all data from JSON file")
    g5.add_argument("--output", "-o",    metavar="FILE", default="portfolio.html",
                    help="Output filename (default: portfolio.html)")
    g5.add_argument("--api-key",         metavar="KEY",
                    help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    g5.add_argument("--no-ai",           action="store_true",
                    help="Skip AI generation — use only provided data")
    g5.add_argument("--export-template", action="store_true",
                    help="Export a JSON template and exit")
    g5.add_argument("--interactive", "-i", action="store_true",
                    help="Force interactive wizard even with args provided")
    g5.add_argument("--quiet", "-q",     action="store_true",
                    help="Suppress animations, minimal output")

    return p


# ══════════════════════════════════════════════════════════════
#  INTERACTIVE WIZARD
# ══════════════════════════════════════════════════════════════

def prompt(label, hint="", required=False, default=""):
    """Styled input prompt."""
    hint_str = f" {c('('+hint+')', C.DIM)}" if hint else ""
    req_str  = c(" *", C.BRED) if required else ""
    default_str = f" {c('['+default+']', C.DIM)}" if default else ""
    
    while True:
        sys.stdout.write(
            f"  {c('▸', C.BCYAN)} {c(label, C.BWHITE)}{req_str}{hint_str}{default_str}: "
        )
        sys.stdout.flush()
        val = input().strip()
        if not val and default:
            return default
        if not val and required:
            cprint(f"  {c('!', C.BRED)} This field is required.", C.DIM)
            continue
        return val

def prompt_list(label, hint="comma-separated"):
    """Input that returns a list."""
    raw = prompt(label, hint)
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]

def prompt_section_header(title, icon="◈"):
    print()
    hr("┄", C.DIM)
    cprint(f"  {icon} {title}", C.BCYAN, C.BOLD)
    hr("┄", C.DIM)

def wizard_experience():
    """Collect experience entries interactively."""
    entries = []
    prompt_section_header("EXPERIENCE", "⌖")
    cprint("  Add work experience. Press Enter with no title to finish.", C.DIM)
    count = 1
    while True:
        print()
        cprint(f"  {c(f'Position #{count}', C.BMAGENTA)}", C.BOLD)
        title = prompt("Job Title", "or press Enter to skip")
        if not title:
            break
        company = prompt("Company")
        start   = prompt("Start Date", "e.g. Jan 2022")
        end     = prompt("End Date",   "e.g. Present", default="Present")
        desc    = prompt("Description", "leave blank → AI generates")
        entries.append({"title": title, "company": company,
                        "start": start, "end": end, "desc": desc})
        count += 1
    return entries

def wizard_education():
    entries = []
    prompt_section_header("EDUCATION", "◫")
    cprint("  Add education entries. Press Enter with no degree to finish.", C.DIM)
    count = 1
    while True:
        print()
        cprint(f"  {c(f'Entry #{count}', C.BMAGENTA)}", C.BOLD)
        degree = prompt("Degree", "or press Enter to skip")
        if not degree:
            break
        inst = prompt("Institution")
        year = prompt("Year")
        gpa  = prompt("GPA / Honors", "optional")
        entries.append({"degree": degree, "institution": inst, "year": year, "gpa": gpa})
        count += 1
    return entries

def wizard_projects():
    entries = []
    prompt_section_header("PROJECTS", "⬡")
    cprint("  Add projects. Press Enter with no name to finish.", C.DIM)
    count = 1
    while True:
        print()
        cprint(f"  {c(f'Project #{count}', C.BMAGENTA)}", C.BOLD)
        name = prompt("Project Name", "or press Enter to skip")
        if not name:
            break
        tech = prompt("Tech Stack", "comma-separated")
        desc = prompt("Description", "leave blank → AI generates")
        url  = prompt("GitHub / URL", "optional")
        entries.append({"name": name, "tech": tech, "desc": desc, "url": url})
        count += 1
    return entries

def wizard_certifications():
    entries = []
    prompt_section_header("CERTIFICATIONS", "◈")
    cprint("  Add certifications. Press Enter with no name to finish.", C.DIM)
    count = 1
    while True:
        print()
        cprint(f"  {c(f'Cert #{count}', C.BMAGENTA)}", C.BOLD)
        name = prompt("Certification Name", "or press Enter to skip")
        if not name:
            break
        issuer = prompt("Issuer")
        year   = prompt("Year")
        cid    = prompt("Credential ID", "optional")
        entries.append({"name": name, "issuer": issuer, "year": year, "id": cid})
        count += 1
    return entries

def run_wizard():
    """Full interactive wizard — returns data dict."""
    cprint("  INTERACTIVE WIZARD MODE", C.BCYAN, C.BOLD)
    cprint("  Fields marked * are required. All others are AI-enhanced if blank.", C.DIM)

    # Identity
    prompt_section_header("IDENTITY", "◈")
    name     = prompt("Full Name",  required=True)
    title    = prompt("Job Title",  required=True)
    email    = prompt("Email")
    location = prompt("Location",  "City, Country")

    # About
    prompt_section_header("ABOUT", "≡")
    cprint("  Leave blank to let AI write your bio based on name + title + skills.", C.DIM)
    about = prompt("Bio / Summary", "or leave blank")

    # Skills
    prompt_section_header("SKILLS", "◉")
    skills_raw = prompt("Skills *", "comma-separated", required=True)
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

    # Links
    prompt_section_header("LINKS", "⟨⟩")
    github    = prompt("GitHub URL",    "optional")
    linkedin  = prompt("LinkedIn URL",  "optional")
    portfolio = prompt("Portfolio URL", "optional")
    twitter   = prompt("Twitter/X URL", "optional")

    # Structured sections
    experience     = wizard_experience()
    education      = wizard_education()
    projects       = wizard_projects()
    certifications = wizard_certifications()

    # API key
    prompt_section_header("API CONFIG", "⚡")
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        cprint(f"  {c('✓', C.BGREEN)} ANTHROPIC_API_KEY found in environment.", C.DIM)
        api_key = env_key
    else:
        api_key = prompt("Anthropic API Key",
                         "or set ANTHROPIC_API_KEY env var — blank = skip AI")

    no_ai = not api_key
    output = prompt("Output filename", "default: portfolio.html", default="portfolio.html")

    return {
        "name": name, "title": title, "email": email, "location": location,
        "about": about, "skills": skills,
        "github": github, "linkedin": linkedin,
        "portfolio": portfolio, "twitter": twitter,
        "experience": experience, "education": education,
        "projects": projects, "certifications": certifications,
        "_api_key": api_key, "_no_ai": no_ai, "_output": output,
    }


# ══════════════════════════════════════════════════════════════
#  DATA BUILDER (from argparse)
# ══════════════════════════════════════════════════════════════

def parse_json_arg(raw, field_name):
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if not isinstance(val, list):
            raise ValueError
        return val
    except (json.JSONDecodeError, ValueError):
        cprint(f"  ! Warning: --{field_name} is not valid JSON, ignoring.", C.BYELLOW)
        return []

def build_data_from_args(args):
    """Merge config file + CLI args into unified data dict."""
    data = {
        "name": "", "title": "", "email": "", "location": "",
        "about": "", "skills": [],
        "github": "", "linkedin": "", "portfolio": "", "twitter": "",
        "experience": [], "education": [], "projects": [], "certifications": [],
    }

    # Load config file first (lowest priority)
    if args.config:
        try:
            with open(args.config) as f:
                cfg = json.load(f)
            data.update(cfg)
            cprint(f"  {c('✓', C.BGREEN)} Config loaded from {args.config}", C.DIM)
        except Exception as e:
            cprint(f"  {c('!', C.BRED)} Could not load config: {e}", C.DIM)

    # CLI args override config
    for field in ["name","title","email","location","about","github","linkedin","portfolio","twitter"]:
        val = getattr(args, field, None)
        if val:
            data[field] = val

    if args.skills:
        data["skills"] = [s.strip() for s in args.skills.split(",") if s.strip()]

    if args.experience:
        data["experience"] = parse_json_arg(args.experience, "experience")
    if args.education:
        data["education"] = parse_json_arg(args.education, "education")
    if args.projects:
        data["projects"] = parse_json_arg(args.projects, "projects")
    if args.certifications:
        data["certifications"] = parse_json_arg(args.certifications, "certifications")

    # API key resolution
    api_key = (
        getattr(args, "api_key", None) or
        os.environ.get("ANTHROPIC_API_KEY", "")
    )
    no_ai = getattr(args, "no_ai", False) or not api_key

    return data, api_key, no_ai


# ══════════════════════════════════════════════════════════════
#  AI CONTENT GENERATION
# ══════════════════════════════════════════════════════════════

def call_claude(api_key, prompt_text, quiet=False):
    """Call Claude API via urllib (no anthropic SDK needed)."""
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt_text}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    response = urllib.request.urlopen(req, timeout=60)
    result = json.loads(response.read().decode("utf-8"))
    return "".join(block.get("text","") for block in result.get("content",[]))

def ai_enhance(data, api_key, quiet=False):
    """Use Claude to fill any missing content fields."""
    needs_about = not data.get("about")
    empty_exp   = [e for e in data.get("experience",[]) if not e.get("desc")]
    empty_proj  = [p for p in data.get("projects",[]) if not p.get("desc")]
    no_exp      = len(data.get("experience",[])) == 0
    no_proj     = len(data.get("projects",[])) == 0

    if not needs_about and not empty_exp and not empty_proj and not no_exp and not no_proj:
        if not quiet:
            cprint(f"  {c('◈', C.BCYAN)} All fields provided — skipping AI generation.", C.DIM)
        return data

    if not quiet:
        print()
        cprint(f"  {c('⚡', C.BYELLOW)} ENGAGING CLAUDE AI  //  Generating missing content…", C.BOLD)

    prompt_text = f"""You are writing professional portfolio content for a developer/tech portfolio.

Person: {data.get('name','a professional')}
Title: {data.get('title','Software Developer')}
Skills: {', '.join(data.get('skills',[]))}
Existing experience: {json.dumps(data.get('experience',[]))}
Existing projects: {json.dumps(data.get('projects',[]))}

Return ONLY valid JSON (no markdown, no backticks, no explanation) with this structure:
{{
  "about": "...",
  "experience": [...],
  "projects": [...]
}}

Rules:
- about: {"Write a first-person professional bio, ~60 words, engaging and specific to their skills." if needs_about else "Return empty string."}
- experience: {"Generate 2 realistic work positions relevant to their title and skills, as [{title,company,start,end,desc}]." if no_exp else "Return same array but fill any empty desc fields. Keep all other data exactly."}
- projects: {"Generate 3 technical projects relevant to their skills, as [{name,tech,desc,url}]. Set url to empty string." if no_proj else "Return same array but fill any empty desc fields. Keep all other data exactly."}

Return pure JSON only."""

    try:
        if not quiet:
            # Animated progress during API call
            frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
            steps = [
                "Analyzing profile data     ",
                "Crafting biography         ",
                "Generating experience      ",
                "Building project showcase  ",
                "Finalizing content         ",
            ]

            import threading
            result_container = [None]
            error_container  = [None]

            def fetch():
                try:
                    result_container[0] = call_claude(api_key, prompt_text, quiet)
                except Exception as e:
                    error_container[0] = e

            thread = threading.Thread(target=fetch)
            thread.start()

            step_i = 0
            frame_i = 0
            while thread.is_alive():
                step = steps[min(step_i, len(steps)-1)]
                frame = frames[frame_i % len(frames)]
                pct = min(95, int((step_i / len(steps)) * 100))
                bar_done = int(pct / 4)
                bar_empty = 25 - bar_done
                bar = (c("▓" * bar_done, C.BCYAN) +
                       c("░" * bar_empty, C.DIM))
                sys.stdout.write(
                    f"\r  {c(frame, C.BMAGENTA)} {c(step, C.DIM)} "
                    f"[{bar}] {c(str(pct)+'%', C.BGREEN)}  "
                )
                sys.stdout.flush()
                time.sleep(0.1)
                frame_i += 1
                if frame_i % 15 == 0:
                    step_i = min(step_i + 1, len(steps) - 1)

            thread.join()
            sys.stdout.write("\r" + " " * 70 + "\r")
            sys.stdout.flush()

            if error_container[0]:
                raise error_container[0]
            raw = result_container[0]
        else:
            raw = call_claude(api_key, prompt_text, quiet)

        # Clean and parse
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)

        if needs_about and parsed.get("about"):
            data["about"] = parsed["about"]

        if no_exp and parsed.get("experience"):
            data["experience"] = parsed["experience"]
        elif empty_exp and parsed.get("experience"):
            for i, orig in enumerate(data["experience"]):
                if not orig.get("desc") and i < len(parsed["experience"]):
                    orig["desc"] = parsed["experience"][i].get("desc","")

        if no_proj and parsed.get("projects"):
            data["projects"] = parsed["projects"]
        elif empty_proj and parsed.get("projects"):
            for i, orig in enumerate(data["projects"]):
                if not orig.get("desc") and i < len(parsed["projects"]):
                    orig["desc"] = parsed["projects"][i].get("desc","")

        if not quiet:
            cprint(f"  {c('✓', C.BGREEN)} AI content generation complete.", C.BOLD)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","replace")
        cprint(f"\n  {c('!', C.BRED)} API error {e.code}: {body[:200]}", C.DIM)
        cprint(f"  {c('→', C.BYELLOW)} Continuing without AI enhancement.", C.DIM)
    except Exception as e:
        cprint(f"\n  {c('!', C.BRED)} AI generation failed: {e}", C.DIM)
        cprint(f"  {c('→', C.BYELLOW)} Continuing without AI enhancement.", C.DIM)

    return data


# ══════════════════════════════════════════════════════════════
#  HTML BUILDER
# ══════════════════════════════════════════════════════════════

def esc(s):
    if not s:
        return ""
    return (str(s)
            .replace("&","&amp;")
            .replace("<","&lt;")
            .replace(">","&gt;")
            .replace('"',"&quot;"))

def svg_github():
    return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>'

def svg_linkedin():
    return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'

def svg_email():
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>'

def svg_pin():
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>'

def svg_link():
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>'

def svg_external():
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'

def build_html(data):
    """Assemble the complete portfolio HTML file."""
    import random

    name     = data.get("name","Your Name")
    title    = data.get("title","Developer")
    email    = data.get("email","")
    location = data.get("location","")
    about    = data.get("about","Passionate developer building the future.")
    skills   = data.get("skills",[])
    github   = data.get("github","")
    linkedin = data.get("linkedin","")
    portfolio= data.get("portfolio","")
    twitter  = data.get("twitter","")
    exp      = data.get("experience",[])
    edu      = data.get("education",[])
    proj     = data.get("projects",[])
    certs    = data.get("certifications",[])

    # Skills HTML
    skills_html = "\n".join(
        f'<div class="skill-item" style="animation-delay:{i*0.06:.2f}s">'
        f'<span class="skill-name">{esc(s)}</span>'
        f'<div class="skill-bar"><div class="skill-fill" style="width:{random.randint(72,98)}%"></div></div>'
        f'</div>'
        for i,s in enumerate(skills)
    )

    # Social links
    social_parts = []
    if github:    social_parts.append(f'<a href="{esc(github)}" target="_blank" class="social-link" title="GitHub">{svg_github()}</a>')
    if linkedin:  social_parts.append(f'<a href="{esc(linkedin)}" target="_blank" class="social-link" title="LinkedIn">{svg_linkedin()}</a>')
    if email:     social_parts.append(f'<a href="mailto:{esc(email)}" class="social-link" title="Email">{svg_email()}</a>')
    if portfolio: social_parts.append(f'<a href="{esc(portfolio)}" target="_blank" class="social-link" title="Website">{svg_link()}</a>')
    social_html = "\n".join(social_parts)

    # Experience timeline
    exp_html = "\n".join(
        f'''<div class="timeline-item reveal">
          <div class="timeline-dot"></div>
          <div class="timeline-card glass-card">
            <div class="tl-header">
              <div><div class="tl-title">{esc(e.get("title",""))}</div>
              <div class="tl-company">{esc(e.get("company",""))}</div></div>
              <div class="tl-date">{esc(e.get("start",""))} — {esc(e.get("end","Present"))}</div>
            </div>
            {f'<p class="tl-desc">{esc(e.get("desc",""))}</p>' if e.get("desc") else ""}
          </div></div>'''
        for e in exp
    )

    # Projects
    proj_html = "\n".join(
        f'''<div class="proj-card glass-card reveal" style="animation-delay:{i*0.1:.1f}s">
          <div class="proj-header">
            <span class="proj-num">0{i+1}</span>
            <h3 class="proj-name">{esc(p.get("name",""))}</h3>
            {f'<a href="{esc(p["url"])}" target="_blank" class="proj-link">{svg_external()}</a>' if p.get("url") else ""}
          </div>
          {f'<p class="proj-desc">{esc(p.get("desc",""))}</p>' if p.get("desc") else ""}
          {f'<div class="proj-tags">' + "".join(f'<span class="tag">{esc(t.strip())}</span>' for t in p.get("tech","").split(",") if t.strip()) + "</div>" if p.get("tech") else ""}
        </div>'''
        for i,p in enumerate(proj)
    )

    # Education
    edu_html = "\n".join(
        f'''<div class="edu-card glass-card reveal">
          <div class="edu-degree">{esc(e.get("degree",""))}</div>
          <div class="edu-inst">{esc(e.get("institution",""))}</div>
          <div class="edu-meta">
            {f'<span>{esc(e["year"])}</span>' if e.get("year") else ""}
            {f'<span class="sep">·</span><span>{esc(e["gpa"])}</span>' if e.get("gpa") else ""}
          </div></div>'''
        for e in edu
    )

    # Certifications
    cert_html = "\n".join(
        f'''<div class="cert-card reveal" style="animation-delay:{i*0.08:.2f}s">
          <div class="cert-icon">⬡</div>
          <div class="cert-info">
            <div class="cert-name">{esc(c_.get("name",""))}</div>
            <div class="cert-meta">{esc(c_.get("issuer",""))}{f" · {esc(c_['year'])}" if c_.get("year") else ""}</div>
          </div></div>'''
        for i,c_ in enumerate(certs)
    )

    # Contact items
    contact_parts = []
    if email:    contact_parts.append(f'<a href="mailto:{esc(email)}" class="contact-item"><span class="ci-icon">{svg_email()}</span><span>{esc(email)}</span></a>')
    if location: contact_parts.append(f'<div class="contact-item"><span class="ci-icon">{svg_pin()}</span><span>{esc(location)}</span></div>')
    if github:   contact_parts.append(f'<a href="{esc(github)}" target="_blank" class="contact-item"><span class="ci-icon">{svg_github()}</span><span>{esc(github.replace("https://",""))}</span></a>')
    if linkedin: contact_parts.append(f'<a href="{esc(linkedin)}" target="_blank" class="contact-item"><span class="ci-icon">{svg_linkedin()}</span><span>{esc(linkedin.replace("https://",""))}</span></a>')
    contact_html = "\n".join(contact_parts)

    # Stats
    stats = []
    if len(skills):  stats.append(f'<div class="stat-card"><div class="stat-num">{len(skills)}+</div><div class="stat-label">Technologies</div></div>')
    if len(exp):     stats.append(f'<div class="stat-card"><div class="stat-num">{len(exp)}</div><div class="stat-label">Positions</div></div>')
    if len(proj):    stats.append(f'<div class="stat-card"><div class="stat-num">{len(proj)}</div><div class="stat-label">Projects</div></div>')
    if len(certs):   stats.append(f'<div class="stat-card"><div class="stat-num">{len(certs)}</div><div class="stat-label">Certifications</div></div>')
    stats_html = "\n".join(stats)

    year = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{esc(name)} — {esc(title)}</title>
<meta name="description" content="{esc(about[:160])}">
<meta name="author" content="{esc(name)}">
<meta property="og:title" content="{esc(name)} — {esc(title)}">
<meta property="og:description" content="{esc(about[:160])}">
<meta property="og:type" content="website">
{f'<meta property="og:url" content="{esc(portfolio)}">' if portfolio else ''}
<meta name="theme-color" content="#00f5ff">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --void:#08080f;--panel:#0f0f1e;--panel2:#141428;--border:#1e1e40;
  --cyan:#00f5ff;--violet:#bf00ff;--magenta:#ff0066;
  --ghost:#c8c8ff;--dim:#6060a0;--white:#f0f0ff;
  --font-mono:'Courier New',Courier,monospace;
  --font-body:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}}
html{{scroll-behavior:smooth}}
body{{background:var(--void);color:var(--ghost);font-family:var(--font-body);
  font-size:15px;line-height:1.7;overflow-x:hidden;}}
body::before{{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(0,245,255,.025) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,245,255,.025) 1px,transparent 1px);
  background-size:60px 60px;pointer-events:none;z-index:0;
  animation:gridDrift 20s linear infinite;}}
@keyframes gridDrift{{0%{{background-position:0 0}}100%{{background-position:60px 60px}}}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;padding:14px 40px;
  background:rgba(8,8,15,.88);backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}}
.nav-logo{{font-family:var(--font-mono);font-size:14px;font-weight:bold;
  color:var(--cyan);text-shadow:0 0 10px rgba(0,245,255,.5);letter-spacing:.05em;}}
.nav-links{{display:flex;gap:28px}}
.nav-links a{{color:var(--dim);text-decoration:none;font-size:13px;
  font-family:var(--font-mono);letter-spacing:.06em;transition:color .2s;}}
.nav-links a:hover{{color:var(--cyan)}}
#hero{{min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:120px 40px 80px;position:relative;z-index:1;text-align:center;}}
.hero-inner{{max-width:780px;width:100%}}
.hero-avatar-ph{{width:130px;height:130px;border-radius:50%;margin:0 auto 32px;
  display:flex;align-items:center;justify-content:center;font-size:52px;
  font-family:var(--font-mono);font-weight:bold;color:var(--cyan);
  background:var(--panel2);
  border:3px solid rgba(0,245,255,.4);
  box-shadow:0 0 30px rgba(0,245,255,.25),0 0 60px rgba(191,0,255,.15);}}
.hero-eyebrow{{font-family:var(--font-mono);font-size:12px;letter-spacing:.2em;
  color:var(--violet);text-transform:uppercase;margin-bottom:16px;}}
.hero-name{{font-size:clamp(36px,7vw,80px);font-weight:800;font-family:var(--font-mono);
  letter-spacing:-.02em;color:var(--white);line-height:1.05;margin-bottom:16px;}}
.hero-name .glow{{color:var(--cyan);text-shadow:0 0 20px rgba(0,245,255,.6),0 0 60px rgba(0,245,255,.3);}}
.hero-title{{font-size:18px;color:var(--dim);margin-bottom:20px;font-family:var(--font-mono);}}
#typed-cursor{{display:inline-block;color:var(--cyan);animation:blink .7s step-end infinite;}}
@keyframes blink{{50%{{opacity:0}}}}
.hero-about{{font-size:16px;color:var(--ghost);max-width:600px;margin:0 auto 36px;line-height:1.7;opacity:.85;}}
.hero-socials{{display:flex;gap:14px;justify-content:center;margin-bottom:40px}}
.social-link{{width:42px;height:42px;border-radius:50%;background:var(--panel2);
  border:1px solid var(--border);display:flex;align-items:center;justify-content:center;
  color:var(--dim);text-decoration:none;transition:all .25s;}}
.social-link:hover{{border-color:var(--cyan);color:var(--cyan);
  box-shadow:0 0 14px rgba(0,245,255,.3);transform:translateY(-2px);}}
.social-link svg{{width:18px;height:18px}}
.hero-cta{{display:flex;gap:14px;justify-content:center;flex-wrap:wrap}}
.cta-btn{{padding:13px 30px;border-radius:6px;font-size:13px;font-family:var(--font-mono);
  font-weight:600;letter-spacing:.06em;cursor:pointer;border:none;text-decoration:none;
  transition:all .2s;display:inline-block;}}
.cta-primary{{background:var(--cyan);color:#000;box-shadow:0 0 20px rgba(0,245,255,.4);}}
.cta-primary:hover{{box-shadow:0 0 30px rgba(0,245,255,.6);transform:translateY(-2px)}}
.cta-secondary{{background:transparent;color:var(--violet);border:1px solid rgba(191,0,255,.5);}}
.cta-secondary:hover{{background:rgba(191,0,255,.1);box-shadow:0 0 16px rgba(191,0,255,.3)}}
section{{padding:100px 40px;max-width:1100px;margin:0 auto;position:relative;z-index:1}}
.section-label{{font-family:var(--font-mono);font-size:11px;letter-spacing:.2em;
  color:var(--violet);text-transform:uppercase;margin-bottom:10px;}}
.section-title{{font-size:clamp(28px,4vw,42px);font-family:var(--font-mono);font-weight:700;
  color:var(--white);margin-bottom:48px;display:flex;align-items:center;gap:16px;}}
.section-title::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border),transparent);}}
.glass-card{{background:rgba(15,15,30,.7);border:1px solid var(--border);border-radius:10px;
  backdrop-filter:blur(12px);transition:border-color .25s,box-shadow .25s;}}
.glass-card:hover{{border-color:rgba(0,245,255,.2);box-shadow:0 4px 30px rgba(0,245,255,.06);}}
#about .about-grid{{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}}
.about-text{{font-size:16px;color:var(--ghost);line-height:1.8;opacity:.9}}
.about-stats{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.stat-card{{padding:20px;border-radius:8px;background:var(--panel2);
  border:1px solid var(--border);text-align:center;}}
.stat-num{{font-family:var(--font-mono);font-size:28px;font-weight:700;color:var(--cyan)}}
.stat-label{{font-size:12px;color:var(--dim);margin-top:4px}}
.skills-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
.skill-item{{display:flex;flex-direction:column;gap:6px;opacity:0;
  animation:fadeUp .5s ease forwards;}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.skill-name{{font-family:var(--font-mono);font-size:12px;letter-spacing:.06em;
  color:var(--ghost);display:flex;align-items:center;gap:6px;}}
.skill-name::before{{content:'▸';color:var(--cyan);font-size:10px}}
.skill-bar{{height:4px;border-radius:2px;background:var(--panel2);overflow:hidden;}}
.skill-fill{{height:100%;border-radius:2px;
  background:linear-gradient(90deg,var(--cyan),var(--violet));
  box-shadow:0 0 8px rgba(0,245,255,.4);animation:fillBar 1.2s ease forwards;}}
@keyframes fillBar{{from{{width:0!important}}to{{}}}}
.timeline{{position:relative;padding-left:32px}}
.timeline::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:1px;
  background:linear-gradient(var(--border),transparent);}}
.timeline-item{{position:relative;margin-bottom:28px}}
.timeline-dot{{position:absolute;left:-38px;top:20px;width:12px;height:12px;
  border-radius:50%;background:var(--cyan);box-shadow:0 0 10px rgba(0,245,255,.5);
  border:2px solid var(--void);}}
.timeline-card{{padding:22px 24px}}
.tl-header{{display:flex;justify-content:space-between;align-items:flex-start;
  gap:16px;margin-bottom:10px;}}
.tl-title{{font-size:16px;font-weight:600;color:var(--white)}}
.tl-company{{color:var(--cyan);font-family:var(--font-mono);font-size:13px;margin-top:2px}}
.tl-date{{font-family:var(--font-mono);font-size:11px;color:var(--dim);
  white-space:nowrap;flex-shrink:0;}}
.tl-desc{{color:var(--ghost);opacity:.8;font-size:14px}}
.proj-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}}
.proj-card{{padding:24px}}
.proj-header{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.proj-num{{font-family:var(--font-mono);font-size:12px;color:var(--dim)}}
.proj-name{{font-size:17px;font-weight:600;color:var(--white);flex:1}}
.proj-link{{color:var(--dim);text-decoration:none;transition:color .2s}}
.proj-link:hover{{color:var(--cyan)}}
.proj-link svg{{width:16px;height:16px}}
.proj-desc{{color:var(--ghost);opacity:.8;font-size:14px;margin-bottom:16px;line-height:1.6}}
.proj-tags{{display:flex;flex-wrap:wrap;gap:6px}}
.tag{{background:rgba(0,245,255,.08);border:1px solid rgba(0,245,255,.2);border-radius:20px;
  padding:3px 10px;font-family:var(--font-mono);font-size:11px;color:var(--cyan);}}
.edu-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}}
.edu-card{{padding:22px}}
.edu-degree{{font-size:16px;font-weight:600;color:var(--white);margin-bottom:4px}}
.edu-inst{{color:var(--cyan);font-family:var(--font-mono);font-size:13px;margin-bottom:10px}}
.edu-meta{{display:flex;align-items:center;gap:8px;font-family:var(--font-mono);
  font-size:12px;color:var(--dim);}}
.sep{{color:var(--border)}}
.certs-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}
.cert-card{{display:flex;align-items:center;gap:16px;padding:18px 20px;
  border-radius:8px;background:var(--panel2);border:1px solid var(--border);
  transition:border-color .2s;}}
.cert-card:hover{{border-color:rgba(191,0,255,.3)}}
.cert-icon{{font-size:22px;color:var(--violet);flex-shrink:0}}
.cert-name{{font-size:14px;font-weight:600;color:var(--white)}}
.cert-meta{{font-family:var(--font-mono);font-size:11px;color:var(--dim);margin-top:3px}}
#contact{{text-align:center}}
.contact-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px;max-width:700px;margin:0 auto 40px;}}
.contact-item{{display:flex;align-items:center;gap:12px;padding:16px 20px;
  border-radius:8px;background:var(--panel2);border:1px solid var(--border);
  color:var(--ghost);text-decoration:none;font-size:14px;transition:all .2s;}}
.contact-item:hover{{border-color:var(--cyan);color:var(--cyan)}}
.ci-icon{{flex-shrink:0;display:flex}}
.ci-icon svg{{width:18px;height:18px}}
footer{{text-align:center;padding:40px;border-top:1px solid var(--border);
  font-family:var(--font-mono);font-size:12px;color:var(--dim);position:relative;z-index:1;}}
footer span{{color:var(--cyan)}}
.reveal{{opacity:0}}
.reveal.revealed{{animation:fadeUp .6s ease forwards}}
@media(max-width:768px){{
  nav{{padding:14px 20px}}.nav-links{{display:none}}
  section{{padding:70px 20px}}#hero{{padding:100px 20px 60px}}
  #about .about-grid{{grid-template-columns:1fr}}.skills-grid{{grid-template-columns:1fr}}
  .tl-header{{flex-direction:column;gap:4px}}
}}
@media(prefers-reduced-motion:reduce){{
  *{{animation-duration:.01ms!important;transition-duration:.01ms!important}}
}}
</style>
</head>
<body>
<nav>
  <div class="nav-logo">&lt;{esc(name.split()[0] if name else 'Portfolio')}/&gt;</div>
  <div class="nav-links">
    <a href="#about">About</a>
    <a href="#skills">Skills</a>
    {('<a href="#experience">Experience</a>' if exp else '')}
    {('<a href="#projects">Projects</a>' if proj else '')}
    {('<a href="#education">Education</a>' if edu or certs else '')}
    <a href="#contact">Contact</a>
  </div>
</nav>

<section id="hero">
  <div class="hero-inner">
    <div class="hero-avatar-ph">{esc(name[0].upper()) if name else '?'}</div>
    <div class="hero-eyebrow">// Portfolio</div>
    <h1 class="hero-name"><span class="glow">{esc(name)}</span></h1>
    <div class="hero-title"><span id="typed-role"></span><span id="typed-cursor">_</span></div>
    <p class="hero-about">{esc(about)}</p>
    <div class="hero-socials">{social_html}</div>
    <div class="hero-cta">
      {f'<a href="mailto:{esc(email)}" class="cta-btn cta-primary">Contact Me</a>' if email else ''}
      {f'<a href="#projects" class="cta-btn cta-secondary">View Projects</a>' if proj else ''}
    </div>
  </div>
</section>

<section id="about">
  <div class="section-label">// 01</div>
  <div class="section-title">About Me</div>
  <div class="about-grid">
    <p class="about-text">{esc(about)}</p>
    <div class="about-stats">{stats_html}</div>
  </div>
</section>

{f'''<section id="skills">
  <div class="section-label">// 02</div>
  <div class="section-title">Skills</div>
  <div class="skills-grid">{skills_html}</div>
</section>''' if skills else ''}

{f'''<section id="experience">
  <div class="section-label">// 03</div>
  <div class="section-title">Experience</div>
  <div class="timeline">{exp_html}</div>
</section>''' if exp else ''}

{f'''<section id="projects">
  <div class="section-label">// 04</div>
  <div class="section-title">Projects</div>
  <div class="proj-grid">{proj_html}</div>
</section>''' if proj else ''}

{f'''<section id="education">
  <div class="section-label">// 05</div>
  <div class="section-title">Education</div>
  <div class="edu-grid">{edu_html}</div>
</section>''' if edu else ''}

{f'''<section id="certifications">
  <div class="section-label">// 06</div>
  <div class="section-title">Certifications</div>
  <div class="certs-grid">{cert_html}</div>
</section>''' if certs else ''}

<section id="contact">
  <div class="section-label">// 07</div>
  <div class="section-title" style="justify-content:center">Get In Touch</div>
  <div class="contact-grid">{contact_html}</div>
  <p style="color:var(--dim);font-family:var(--font-mono);font-size:12px">
    Open to opportunities · Collaborations · Consulting
  </p>
</section>

<footer>
  <p>Designed &amp; built by <span>{esc(name)}</span> · {year}</p>
  <p style="margin-top:6px;font-size:11px">Generated with RESUME.GEN · AI Hacker Portfolio CLI</p>
</footer>

<script>
(function(){{
  var roles=[{json.dumps(title)},{json.dumps(skills[0]+' Expert') if skills else '""'}];
  var ri=0,ci=0,del=false;
  var el=document.getElementById('typed-role');
  function tick(){{
    var word=roles[ri]||'';
    if(!del){{el.textContent=word.slice(0,++ci);if(ci===word.length){{del=true;setTimeout(tick,1800);return;}}}}
    else{{el.textContent=word.slice(0,--ci);if(ci===0){{del=false;ri=(ri+1)%roles.length;setTimeout(tick,400);return;}}}}
    setTimeout(tick,del?60:90);
  }}
  tick();
}})();
(function(){{
  var obs=new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('revealed');obs.unobserve(e.target);}}}});
  }},{{threshold:.12}});
  document.querySelectorAll('.reveal,.timeline-item,.proj-card,.cert-card,.edu-card').forEach(function(el){{obs.observe(el);}});
}})();
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
#  SUMMARY DISPLAY
# ══════════════════════════════════════════════════════════════

def show_summary(data, quiet=False):
    if quiet:
        return
    print()
    hr("─", C.DIM)
    cprint("  DATA SUMMARY", C.BCYAN, C.BOLD)
    hr("─", C.DIM)

    def row(label, val, col=C.BWHITE):
        if val:
            print(f"  {c(label.ljust(18), C.DIM)} {c(str(val), col)}")

    row("Name",          data.get("name"))
    row("Title",         data.get("title"), C.BMAGENTA)
    row("Email",         data.get("email"))
    row("Location",      data.get("location"))
    row("Skills",        f"{len(data.get('skills',[]))} items", C.BCYAN)
    row("Experience",    f"{len(data.get('experience',[]))} positions", C.BYELLOW)
    row("Projects",      f"{len(data.get('projects',[]))} items", C.BYELLOW)
    row("Education",     f"{len(data.get('education',[]))} entries", C.BYELLOW)
    row("Certifications",f"{len(data.get('certifications',[]))} items", C.BYELLOW)
    if data.get("github"):   row("GitHub",       data["github"], C.DIM)
    if data.get("linkedin"): row("LinkedIn",     data["linkedin"], C.DIM)
    hr("─", C.DIM)
    print()

def show_final(output_path, quiet=False):
    size = os.path.getsize(output_path)
    size_str = f"{size/1024:.1f} KB"

    if quiet:
        print(output_path)
        return

    print()
    hr("═", C.BGREEN)
    cprint("  ✓  PORTFOLIO GENERATED SUCCESSFULLY", C.BGREEN, C.BOLD)
    hr("═", C.BGREEN)
    print()
    cprint(f"  {c('Output file:', C.DIM)} {c(output_path, C.BCYAN, C.BOLD)}")
    cprint(f"  {c('File size:', C.DIM)}   {c(size_str, C.BGREEN)}")
    cprint(f"  {c('Status:', C.DIM)}      {c('Self-contained · No dependencies · Deploy anywhere', C.DIM)}")
    print()
    cprint("  HOW TO USE:", C.BWHITE, C.BOLD)
    cprint(f"  1. Open in browser:   {c('open '+output_path, C.BCYAN)}")
    cprint(f"  2. Deploy to GitHub Pages — drop the file in your repo")
    cprint(f"  3. Host on Netlify / Vercel — drag & drop the single file")
    print()
    hr("─", C.DIM)
    cprint("  // RESUME.GEN · Mission Complete", C.DIM)
    hr("─", C.DIM)
    print()


# ══════════════════════════════════════════════════════════════
#  TEMPLATE EXPORT
# ══════════════════════════════════════════════════════════════

TEMPLATE = {
    "name": "Alex Mercer",
    "title": "Senior Penetration Tester",
    "email": "alex@mercer.dev",
    "location": "San Francisco, CA",
    "about": "",
    "skills": ["Python", "Bash", "Nmap", "Wireshark", "Metasploit", "Burp Suite", "Linux", "Docker"],
    "github": "https://github.com/alexmercer",
    "linkedin": "https://linkedin.com/in/alexmercer",
    "portfolio": "",
    "twitter": "",
    "experience": [
        {"title": "Senior Pentester", "company": "Phantom Security", "start": "2022", "end": "Present", "desc": ""},
        {"title": "Security Analyst", "company": "NetDefend LLC",    "start": "2020", "end": "2022",    "desc": ""}
    ],
    "education": [
        {"degree": "B.Sc. Computer Science", "institution": "MIT", "year": "2019", "gpa": "3.8"}
    ],
    "projects": [
        {"name": "PacketScope", "tech": "Python, Scapy, Rich", "desc": "", "url": ""},
        {"name": "NetForge",    "tech": "PyQt6, Scapy",        "desc": "", "url": ""}
    ],
    "certifications": [
        {"name": "CompTIA Security+", "issuer": "CompTIA", "year": "2023", "id": ""},
        {"name": "CEH",               "issuer": "EC-Council","year": "2024", "id": ""}
    ]
}

def export_template(path="resume_template.json"):
    with open(path, "w") as f:
        json.dump(TEMPLATE, f, indent=2)
    cprint(f"\n  {c('✓', C.BGREEN)} Template exported to {c(path, C.BCYAN)}", C.BOLD)
    cprint(f"  Edit the file, then run:", C.DIM)
    cprint(f"  {c('python resume_gen.py --config '+path, C.BCYAN)}")
    print()


# ══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main():
    parser = build_parser()
    args   = parser.parse_args()

    # Export template mode
    if args.export_template:
        export_template()
        return

    quiet = args.quiet

    # Boot sequence
    if not quiet:
        boot_sequence()

    # Decide: interactive or args-driven
    has_args = bool(args.name or args.title or args.skills or args.config)

    if not has_args or args.interactive:
        # Interactive wizard
        if not quiet:
            typewrite("  Entering interactive wizard…", delay=0.025, color=C.BCYAN)
            print()
        try:
            wiz = run_wizard()
        except KeyboardInterrupt:
            print()
            cprint("\n  Interrupted. Exiting.", C.DIM)
            return

        data = {
            k: v for k, v in wiz.items()
            if not k.startswith("_")
        }
        api_key = wiz.get("_api_key","")
        no_ai   = wiz.get("_no_ai", True)
        output  = wiz.get("_output","portfolio.html")
    else:
        # Args-driven mode
        data, api_key, no_ai = build_data_from_args(args)
        output = args.output
        if not quiet:
            typewrite("  Args parsed. Building your portfolio…", delay=0.02, color=C.BCYAN)

    # Validate minimums
    if not data.get("name"):
        cprint(f"\n  {c('✗', C.BRED)} --name is required. Use --help for usage.", C.BOLD)
        sys.exit(1)
    if not data.get("title"):
        cprint(f"\n  {c('✗', C.BRED)} --title is required.", C.BOLD)
        sys.exit(1)
    if not data.get("skills"):
        cprint(f"\n  {c('✗', C.BRED)} --skills is required (comma-separated list).", C.BOLD)
        sys.exit(1)

    # Show summary
    show_summary(data, quiet)

    # AI enhancement
    if not no_ai and api_key:
        data = ai_enhance(data, api_key, quiet)
    elif not quiet and no_ai:
        cprint(f"  {c('◌', C.DIM)} Skipping AI — generating from provided data only.", C.DIM)

    # Build HTML
    if not quiet:
        print()
        cprint(f"  {c('⬡', C.BMAGENTA)} Building HTML…", C.BOLD, end=" ")
        sys.stdout.flush()

    html = build_html(data)

    if not quiet:
        cprint(c("done", C.BGREEN), C.BOLD)
        progress_bar("Embedding CSS & JS", width=38, color=C.BCYAN)
        progress_bar("Optimizing output  ", width=38, color=C.BMAGENTA)

    # Write file
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    show_final(output, quiet)


if __name__ == "__main__":
    main()
