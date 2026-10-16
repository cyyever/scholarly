"""Command line interface for scholarly."""

import argparse
import json
import sys

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

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
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
