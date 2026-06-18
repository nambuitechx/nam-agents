"""CLI for embedding documents into OpenSearch."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from core.service import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    EmbeddingService,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Embed documents into OpenSearch")
    subparsers = parser.add_subparsers(dest="command", required=True)

    embed_parser = subparsers.add_parser("embed", help="Embed a file")
    embed_parser.add_argument("--file", required=True, type=Path, help="Path to document")
    embed_parser.add_argument(
        "--document-id",
        default=None,
        help="Optional client UUID (server generates one if omitted)",
    )
    embed_parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing document with the same ID",
    )

    remove_parser = subparsers.add_parser("remove", help="Remove a document")
    remove_parser.add_argument("--document-id", required=True, help="Document UUID")

    list_parser = subparsers.add_parser("list", help="List chunks or documents")
    group = list_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--document-id", help="List chunks for one document")
    group.add_argument("--all", action="store_true", help="List all documents")

    return parser


async def _run(args: argparse.Namespace) -> int:
    service = EmbeddingService()
    try:
        if args.command == "embed":
            result = await service.embed_file(
                document_id=args.document_id,
                path=args.file,
                replace=args.replace,
            )
            print(
                json.dumps(
                    {
                        "document_id": result.document_id,
                        "filename": result.filename,
                        "chunk_count": result.chunk_count,
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "remove":
            deleted = await service.remove_document(args.document_id)
            print(json.dumps({"document_id": args.document_id, "deleted_chunks": deleted}, indent=2))
            return 0

        if args.command == "list":
            if args.all:
                documents = await service.list_documents()
                print(json.dumps({"documents": documents}, indent=2))
            else:
                chunks = await service.list_chunks(args.document_id)
                print(json.dumps({"document_id": args.document_id, "chunks": chunks}, indent=2))
            return 0

        raise RuntimeError(f"Unknown command: {args.command}")
    except (DocumentAlreadyExistsError, DocumentNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await service.close()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
