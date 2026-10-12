import hashlib
import json
import os
import random
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict
from app.config import format_print_datetime
from app.module_registry import register_module
import feedparser
import requests

_selection_lock = threading.Lock()

@register_module(
    type_id="wotd",
    label="Word of the Day",
    description="Prints an English online or Russian offline word of the day",
    icon="book",
    offline=False,
    category="content",
    config_schema={
        "type": "object",
        "properties": {
            "language": {"type": "string", "title": "Language / Язык", "enum": ["en", "ru"], "default": "en"}
        },
    },
)
def format_text_receipt(printer, config: Dict[str, Any] = None, module_name: str = None):
    language = (config or {}).get("language", "en")
    if language == "ru":
        printer.print_header(module_name or "СЛОВО ДНЯ", icon="book")
        printer.print_caption(format_print_datetime(time_format="24h", date_format="%d.%m.%Y"))
        printer.print_line()
        try:
            word = get_russian_word_of_day()
        except (OSError, ValueError, json.JSONDecodeError):
            printer.print_body("Не удалось загрузить словарь.")
            return
        if word is None:
            printer.print_body("В словаре нет подходящих слов.")
            return
        printer.print_bold(word.get("stressed_word") or word["word"])
        printer.print_body(word["definition"])
        if word.get("example"):
            printer.feed(1)
            printer.print_caption(word["example"])
        return

    try:
        # Use requests with timeout instead of feedparser directly
        # This prevents hanging on slow/unresponsive feeds
        response = requests.get("https://www.merriam-webster.com/wotd/feed/rss2", timeout=10)
        response.raise_for_status()

        # Parse the fetched content
        feed = feedparser.parse(response.content)

        if not feed.entries:
            return
        
        # We only care about the first entry
        entry = feed.entries[0]

        word = entry.get("title", "No Word")
        definition = entry.get("merriam_shortdef", "No Definition")

        printer.print_header(module_name or "WORD OF THE DAY", icon="book")
        printer.print_caption(format_print_datetime())
        printer.print_line()

        printer.print_bold(word)
        printer.print_body(definition)

    except Exception:
        return


def get_russian_word_of_day(day: date = None) -> Dict[str, str] | None:
    """Cycle through the offline words across prints and service restarts."""
    path = Path(__file__).resolve().parent.parent / "data" / "wotd_ru.json"
    with path.open(encoding="utf-8") as handle:
        entries = json.load(handle)
    if not isinstance(entries, list):
        raise ValueError("Expected a list of words")
    words = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("review_status") == "needs_review":
            continue
        word = entry.get("word")
        definition = entry.get("definition")
        if not isinstance(word, str) or not word.strip() or not isinstance(definition, str) or not definition.strip():
            continue
        words.setdefault(word.strip().casefold(), entry)
    if not words:
        return None
    ordered = sorted(words)
    state_path = Path(__file__).resolve().parent.parent / "data" / "wotd_ru_state.json"
    with _selection_lock:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            state = {}
        signature = hashlib.sha256("\n".join(ordered).encode("utf-8")).hexdigest()
        sequence = state.get("sequence") if state.get("signature") == signature else None
        position = state.get("position", 0) if sequence is not None else 0
        if not isinstance(sequence, list) or len(sequence) != len(ordered) or set(sequence) != set(ordered) or not isinstance(position, int) or not 0 <= position <= len(sequence):
            sequence = ordered.copy()
            random.shuffle(sequence)
            position = 0
        if position == len(sequence):
            previous = sequence[-1]
            random.shuffle(sequence)
            if len(sequence) > 1 and sequence[0] == previous:
                sequence[0], sequence[1] = sequence[1], sequence[0]
            position = 0
        selected = sequence[position]
        next_state = {"signature": signature, "sequence": sequence, "position": position + 1}
        temporary = state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(next_state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, state_path)
    return words[selected]
