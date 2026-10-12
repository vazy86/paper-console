"""Deterministic full-receipt preview using the production bitmap pipeline."""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from testing.render_all_prints import CapturePrinter, _save_single_bitmap
from app.modules.quotes import format_quotes_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('testing/artifacts/debug/quotes_ru.png'))
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)
    printer = CapturePrinter()
    printer.reset_buffer(max_lines=0)
    format_quotes_receipt(printer, {'language': 'ru'})
    printer.flush_buffer()
    print(_save_single_bitmap(printer, args.output))


if __name__ == '__main__':
    main()
