import csv
import random
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.crossword import CrosswordGenerator, execute_crossword, normalize_answer
from app.drivers.printer_serial import PrinterDriver

DATA = Path(__file__).resolve().parents[1] / 'app/data/crossword_words_ru.csv'


def test_russian_dictionary_quality():
    rows = list(csv.DictReader(DATA.open(encoding='utf-8')))
    words = [r['word'].upper().replace('Ё', 'Е') for r in rows]
    assert len(words) >= 200
    assert len(words) == len(set(words))
    assert {r['difficulty'] for r in rows} == {'easy', 'hard'}
    for r, word in zip(rows, words):
        assert 3 <= len(word) <= 8
        assert all('А' <= c <= 'Я' for c in word)
        assert r['hint'].strip()


def test_cyrillic_survives_bitmap_sanitizer():
    printer = PrinterDriver(init_serial=False)
    assert printer._sanitize_text('Ёж, йод, СЪЕЗД и ЩУКА') == 'Ёж, йод, СЪЕЗД и ЩУКА'
    assert printer._sanitize_text('Café — test') == 'Cafe - test'


def test_yo_normalized_only_in_answers():
    assert normalize_answer('  клён ', 'ru') == 'КЛЕН'
    assert normalize_answer('ёжик', 'ru') == 'ЕЖИК'


def test_full_russian_receipt_bitmap():
    from testing.render_all_prints import CapturePrinter
    random.seed(42)
    printer = CapturePrinter()
    printer.reset_buffer(max_lines=0)
    execute_crossword(printer, {'language': 'ru', 'num_words': 8})
    printer.flush_buffer()
    assert len(printer.captured_bitmaps) == 1
    image = printer.captured_bitmaps[0]
    assert image.width == 384
    assert image.height > 400
    assert image.convert('L').getextrema() == (0, 255)


@pytest.mark.parametrize('config', [{}, {'language': 'en'}, {'language': '../../bad'}])
def test_english_compatibility(config):
    printer = MagicMock()
    printer.PRINTER_WIDTH_DOTS = 384
    random.seed(42)
    execute_crossword(printer, config)
    printer.print_header.assert_called_with('CROSSWORD', icon='grid-nine')
    assert any(c.args[0].startswith('ANSWERS: ') for c in printer.print_caption.call_args_list)


@pytest.mark.parametrize('difficulty', ['Easy', 'Medium', 'Hard'])
def test_russian_receipt(difficulty):
    printer = MagicMock()
    printer.PRINTER_WIDTH_DOTS = 384
    random.seed(42)
    execute_crossword(printer, {'language': 'ru', 'difficulty': difficulty, 'num_words': 8})
    printer.print_header.assert_called_with('КРОССВОРД', icon='grid-nine')
    printer.print_image.assert_called_once()
    captions = [c.args[0] for c in printer.print_caption.call_args_list]
    assert any(c.startswith('ОТВЕТЫ: ') for c in captions)
    assert not any('ANSWERS' in c for c in captions)


@pytest.mark.parametrize('seed', range(6))
def test_russian_grid_invariants(seed):
    rows = list(csv.DictReader(DATA.open(encoding='utf-8')))
    pool = [(r['word'].upper().replace('Ё', 'Е'), r['hint']) for r in rows]
    random.seed(seed)
    gen = CrosswordGenerator(8, 8)
    gen.generate(pool, 10)
    assert 3 <= len(gen.words_placed) <= 10
    assert len({p['word'] for p in gen.words_placed}) == len(gen.words_placed)
    occupied = {}
    for p in gen.words_placed:
        for i, letter in enumerate(p['word']):
            x = p['x'] + (i if p['dir'] == 'across' else 0)
            y = p['y'] + (i if p['dir'] == 'down' else 0)
            assert 0 <= x < 8 and 0 <= y < gen.height
            assert gen.grid[y][x] == letter
            assert occupied.get((x, y), letter) == letter
            occupied[x, y] = letter
    starts = sorted({(p['y'], p['x']) for p in gen.words_placed})
    for p in gen.words_placed:
        assert p['num'] == starts.index((p['y'], p['x'])) + 1
