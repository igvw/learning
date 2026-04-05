from __future__ import annotations

import argparse
from pathlib import Path

from .database import get_connection, initialize_database
from .services import sync_seed_content
from .settings import CONTENT_DIR, resolve_db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Learning app maintenance commands.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    sync_parser = subcommands.add_parser("import-content", help="Import any missing seed content into SQLite.")
    sync_parser.add_argument("--db-path", default=str(resolve_db_path()))
    sync_parser.add_argument("--content-root", default=str(CONTENT_DIR))

    args = parser.parse_args()
    if args.command == "import-content":
        initialize_database(args.db_path)
        with get_connection(args.db_path) as connection:
            result = sync_seed_content(connection, Path(args.content_root))
        print(f"Imported {result['modules']} modules and {result['questions']} questions.")


if __name__ == "__main__":
    main()
