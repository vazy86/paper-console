"""Deterministic full-receipt preview using the production bitmap pipeline."""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from testing.render_all_prints import CapturePrinter, _save_single_bitmap
from app.modules.crossword import execute_crossword


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('testing/artifacts/debug/crossword_ru.png'))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--difficulty', choices=['Easy', 'Medium', 'Hard'], default='Easy')
    parser.add_argument('--words', type=int, default=8)
    args = parser.parse_args()
    random.seed(args.seed)
    printer = CapturePrinter()
    printer.reset_buffer(max_lines=0)
    execute_crossword(printer, {'language': 'ru', 'difficulty': args.difficulty, 'num_words': args.words})
    printer.flush_buffer()
    print(_save_single_bitmap(printer, args.output))


if __name__ == '__main__':
    main()
