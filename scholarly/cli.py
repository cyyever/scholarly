"""Command line interface for scholarly."""

import argparse
from collections import Counter
import json
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.model import DuplicateBlockKeyBlock, Entry
from . import scholarly as api


def _write_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scholarly",
        description="Search Google Scholar for publications and authors.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publications = subparsers.add_parser("search-pubs", help="search publications")
    publications.add_argument("query", help="publication search terms")
    publications.add_argument("--limit", type=int, default=10,
                              help="maximum results to return (default: 10)")
    publications.add_argument("--filled", action="store_true",
                              help="fetch full details for each result")

    authors = subparsers.add_parser("search-author", help="search authors")
    authors.add_argument("name", help="author name or affiliation")
    authors.add_argument("--limit", type=int, default=10,
                         help="maximum results to return (default: 10)")

    bibliography = subparsers.add_parser(
        "scan-bib", help="scan a BibTeX file for entries and missing fields"
    )
    bibliography.add_argument("file", type=Path, help="path to a .bib file")
    bibliography.add_argument(
        "--required-fields", default="title,author,year",
        help="comma-separated fields to check (default: title,author,year)",
    )

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "scan-bib":
            required_fields = [
                field.strip().lower()
                for field in args.required_fields.split(",")
                if field.strip()
            ]
            library = bibtexparser.parse_string(
                args.file.read_text(encoding="utf-8-sig")
            )
            entries = [block for block in library.blocks if isinstance(block, Entry)]
            keys = [entry.key for entry in entries]
            duplicate_keys = sorted({
                block.key for block in library.blocks
                if isinstance(block, DuplicateBlockKeyBlock)
            } | {
                key for key, count in Counter(keys).items()
                if key and count > 1
            })
            missing_fields = []
            for entry in entries:
                fields = {field.key.lower(): str(field.value).strip()
                          for field in entry.fields}
                missing = [field for field in required_fields if not fields.get(field)]
                if missing:
                    missing_fields.append({"key": entry.key, "fields": missing})
            parse_issues = [
                {"type": type(block).__name__,
                 "details": str(getattr(block, "error", block))}
                for block in library.blocks if not isinstance(block, Entry)
            ]
            _write_json({
                "file": str(args.file),
                "entry_count": len(entries),
                "entry_types": dict(sorted(Counter(
                    entry.entry_type for entry in entries
                ).items())),
                "required_fields": required_fields,
                "missing_fields": missing_fields,
                "duplicate_keys": duplicate_keys,
                "parse_issues": parse_issues,
            })
            return 0

        if args.limit < 1:
            parser.error("--limit must be at least 1")
        if args.command == "search-pubs":
            results = []
            for publication in api.search_pubs(args.query):
                if args.filled:
                    publication = api.fill(publication)
                results.append(publication)
                if len(results) >= args.limit:
                    break
        else:
            results = []
            for author in api.search_author(args.name):
                results.append(author)
                if len(results) >= args.limit:
                    break
        _write_json(results)
        return 0
    except (KeyboardInterrupt, BrokenPipeError):
        return 130
    except Exception as exc:
        print(f"scholarly: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
