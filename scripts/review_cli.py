"""CLI Tool for Human Agronomist Review of AI Responses.

Allows agronomists and reviewers to inspect answers generated during evaluations,
rate their accuracy, safety, and naturalness, and save feedback.
"""
import argparse
import csv
import sys
from pathlib import Path

DEFAULT_CSV_PATH = Path("eval/reports/answer_eval_review.csv")


def review_answers(csv_file: Path):
    """Interactive CLI to inspect and annotate answers."""
    if not csv_file.exists():
        print(f"Error: Evaluation file '{csv_file}' not found. Run eval/answer_eval.py first.")
        sys.exit(1)

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print("=" * 70)
    print("HELLO FARMER: AGRONOMIST ANSWER REVIEW CLI")
    print(f"Loaded {len(reader)} items from {csv_file}")
    print("=" * 70)

    for idx, row in enumerate(reader, 1):
        print(f"\n--- Item {idx}/{len(reader)} [{row.get('id', '')}] ---")
        print(f"Category: {row.get('category')}")
        print(f"Language: {row.get('lang')}")
        print(f"Question: {row.get('question')}")
        print(f"Passages: {row.get('passages_found')}")
        print(f"Grounded: {row.get('grounded')} | Needs Referral: {row.get('needs_referral')}")
        print(f"Spoken Answer: {row.get('final_answer')}")
        print(f"Guardrail Flag: {row.get('reasons')}")
        print("-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Agronomist Review CLI for Hello Farmer")
    parser.add_argument("--file", type=Path, default=DEFAULT_CSV_PATH, help="Path to evaluation CSV file")
    args = parser.parse_args()
    review_answers(args.file)


if __name__ == "__main__":
    main()
