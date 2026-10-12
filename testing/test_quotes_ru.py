import json
from unittest.mock import Mock
import pytest
from app.modules import quotes


def test_corpus():
    rows = json.loads(quotes._get_quotes_db_path("ru").read_text())
    assert len(rows) == 146
    assert all(row["quoteText"] and isinstance(row["quoteAuthor"], str) for row in rows)
    assert len({row["quoteText"] for row in rows}) == len(rows)


def test_default_keeps_english():
    assert quotes._get_quotes_db_path().name == "quotes.json"
    assert quotes._get_quotes_db_path("unsupported").name == "quotes.json"


@pytest.mark.parametrize("language,title", [("en", "QUOTE"), ("ru", "ЦИТАТА ДНЯ")])
def test_receipt(monkeypatch, language, title):
    get = Mock(return_value={"quoteText": "Первая\nстрока", "quoteAuthor": "Автор"})
    monkeypatch.setattr(quotes, "get_random_quote", get)
    printer = Mock()
    quotes.format_quotes_receipt(printer, {"language": language})
    get.assert_called_once_with(language)
    printer.print_header.assert_called_once_with(title, icon="quotes")
    printer.print_body.assert_called_once_with('"Первая строка"')
    assert printer.print_caption.call_args.args == ("— Автор",)


def test_custom_title_and_anonymous(monkeypatch):
    monkeypatch.setattr(quotes, "get_random_quote", lambda language: {"quoteText": "Текст", "quoteAuthor": ""})
    printer = Mock()
    quotes.format_quotes_receipt(printer, {"language": "ru"}, "Мои цитаты")
    printer.print_header.assert_called_once_with("Мои цитаты", icon="quotes")
    assert printer.print_caption.call_count == 1


@pytest.mark.parametrize("contents", ["[]", "{}", "broken json"])
def test_bad_database(monkeypatch, tmp_path, contents):
    path = tmp_path / "quotes.json"
    path.write_text(contents)
    monkeypatch.setattr(quotes, "_get_quotes_db_path", lambda language: path)
    assert quotes.get_random_quote("ru")["quoteAuthor"] == "Система"
