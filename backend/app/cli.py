import argparse
from pathlib import Path

from .database import get_connection, initialize_database
from .services import sync_seed_content
from .settings import CONTENT_DIR, resolve_database_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Learning app maintenance commands.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init-db", help="Initialize the PostgreSQL schema.")
    init_parser.add_argument("--database-url")

    sync_parser = subcommands.add_parser("import-content", help="Import any missing seed content into PostgreSQL.")
    sync_parser.add_argument("--database-url")
    sync_parser.add_argument("--content-root", default=str(CONTENT_DIR))

    args = parser.parse_args()
    database_url = resolve_database_url(args.database_url)
    if args.command == "init-db":
        initialize_database(database_url)
        print("Database initialized.")
    elif args.command == "import-content":
        initialize_database(database_url)
        with get_connection(database_url) as connection:
            result = sync_seed_content(connection, Path(args.content_root))
        print(f"Imported {result['modules']} modules and {result['questions']} questions.")


if __name__ == "__main__":
    main()
