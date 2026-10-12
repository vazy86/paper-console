import json
import random
from typing import Dict, Any
from pathlib import Path
from app.config import format_print_datetime
from app.module_registry import register_module


# Resolve path relative to the app package directory.
def _get_quotes_db_path(language: str = "en") -> Path:
    """Get the quotes database path relative to the app package."""
    filename = "quotes_ru.json" if language == "ru" else "quotes.json"
    return Path(__file__).resolve().parent.parent / "data" / filename


LOCAL_DB_PATH = _get_quotes_db_path()


def get_random_quote(language: str = "en") -> Dict[str, str]:
    """Reads a random quote from the local database."""
    try:
        quotes_path = _get_quotes_db_path(language)
        with open(quotes_path, "r", encoding="utf-8") as f:
            quotes = json.load(f)
            if not quotes:
                return {"quoteText": "Цитаты не найдены." if language == "ru" else "No quotes found.", "quoteAuthor": "Система" if language == "ru" else "System"}
            if not isinstance(quotes, list):
                return {
                    "quoteText": "Неверный формат базы цитат." if language == "ru" else "Invalid quotes database format.",
                    "quoteAuthor": "Система" if language == "ru" else "System",
                }
            return random.choice(quotes)
    except FileNotFoundError:
        return {
            "quoteText": "Локальная база цитат отсутствует." if language == "ru" else "Offline quotes database is missing.",
            "quoteAuthor": "Система" if language == "ru" else "System",
        }
    except json.JSONDecodeError as e:
        return {
            "quoteText": "Ошибка JSON в базе цитат." if language == "ru" else f"Invalid JSON in quotes database: {e}",
            "quoteAuthor": "Система" if language == "ru" else "System",
        }
    except Exception as e:
        return {
            "quoteText": "Не удалось прочитать базу цитат." if language == "ru" else f"Error reading quotes database: {str(e)}",
            "quoteAuthor": "Система" if language == "ru" else "System",
        }


@register_module(
    type_id="quotes",
    label="Daily Quote",
    description="Prints a random offline quote in English or Russian",
    icon="quotes",
    offline=True,
    category="content",
    config_schema={
        "type": "object",
        "properties": {
            "language": {"type": "string", "title": "Language / Язык",
                         "enum": ["en", "ru"], "default": "en"},
        },
    },
)
def format_quotes_receipt(
    printer, config: Dict[str, Any] = None, module_name: str = None
):
    """Prints a random quote."""
    language = (config or {}).get("language", "en")
    quote = get_random_quote(language)
    text = quote.get("quoteText", "")
    author = quote.get("quoteAuthor", "Unknown")

    # Header
    printer.print_header(module_name or ("ЦИТАТА ДНЯ" if language == "ru" else "QUOTE"), icon="quotes")
    printer.print_caption(
        format_print_datetime(time_format="24h", date_format="%d.%m.%Y")
        if language == "ru" else format_print_datetime()
    )
    printer.print_line()

    # Quote body in italics-style (using medium weight for emphasis)
    # Clean text: remove any embedded newlines and normalize whitespace
    import re
    text = re.sub(r'[\n\r\t]+', ' ', text)  # Replace all whitespace chars with single space
    text = " ".join(text.split())  # Normalize multiple spaces to single space
    
    # Don't pre-wrap! Let the printer's font-metric-based wrapping handle it.
    # The printer driver uses _wrap_text_by_width which uses actual font pixel metrics,
    # not character counts. Pre-wrapping with character-based wrap_text causes
    # double-wrapping and incorrect line breaks.
    # 
    # Simply pass the text with quotes - the printer will wrap it correctly based on
    # actual rendered width, and the quotes will naturally be at the start and end.
    printer.print_body(f'"{text}"')

    printer.feed(1)

    # Attribution
    if author:
        printer.print_caption(f"— {author}")
