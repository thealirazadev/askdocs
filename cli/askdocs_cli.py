"""Small CLI client for askdocs: add, list, delete, ask over HTTP.

Talks to a running askdocs server; no direct access to the stores. Base URL and API key come
from CLI flags or environment variables (ASKDOCS_URL, ASKDOCS_API_KEY).
"""

import argparse
import os
import sys

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="askdocs", description="CLI client for askdocs.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ASKDOCS_URL", DEFAULT_BASE_URL),
        help="askdocs server base URL (default: %(default)s, or ASKDOCS_URL).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ASKDOCS_API_KEY", ""),
        help="API key sent as X-API-Key (default: ASKDOCS_API_KEY).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Upload and index a document.")
    add_parser.add_argument("path", help="Path to a .txt, .md, or .pdf file.")

    subparsers.add_parser("list", help="List indexed documents.")

    delete_parser = subparsers.add_parser("delete", help="Delete a document by id.")
    delete_parser.add_argument("id", help="Document id.")

    ask_parser = subparsers.add_parser("ask", help="Ask a question over the indexed corpus.")
    ask_parser.add_argument("question", help="The question to ask.")

    return parser


def _headers(api_key: str) -> dict:
    return {"X-API-Key": api_key} if api_key else {}


def _print_error_and_exit(exc: Exception) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            message = exc.response.json()["error"]["message"]
        except (ValueError, KeyError):
            message = f"Request failed with status {exc.response.status_code}."
        print(f"Error: {message}", file=sys.stderr)
    elif isinstance(exc, httpx.RequestError):
        print(f"Error: could not reach the server ({exc}).", file=sys.stderr)
    else:
        print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)


def cmd_add(client: httpx.Client, path: str) -> None:
    with open(path, "rb") as handle:
        filename = os.path.basename(path)
        response = client.post("/documents", files={"file": (filename, handle)})
    response.raise_for_status()
    body = response.json()
    print(f"Indexed {body['filename']} (id={body['id']}, chunks={body['num_chunks']}).")


def cmd_list(client: httpx.Client) -> None:
    response = client.get("/documents")
    response.raise_for_status()
    documents = response.json()["documents"]
    if not documents:
        print("No documents indexed.")
        return
    for doc in documents:
        print(f"{doc['id']}  {doc['filename']}  chunks={doc['num_chunks']}  status={doc['status']}")


def cmd_delete(client: httpx.Client, document_id: str) -> None:
    response = client.delete(f"/documents/{document_id}")
    response.raise_for_status()
    print(f"Deleted {document_id}.")


def cmd_ask(client: httpx.Client, question: str) -> None:
    response = client.post("/ask", json={"question": question})
    response.raise_for_status()
    body = response.json()
    print(body["answer"])
    if body["citations"]:
        print("\nSources:")
        for citation in body["citations"]:
            print(f"  - {citation['filename']} #{citation['chunk_index']}: {citation['snippet']}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    with httpx.Client(
        base_url=args.base_url, headers=_headers(args.api_key), timeout=30.0
    ) as client:
        try:
            if args.command == "add":
                cmd_add(client, args.path)
            elif args.command == "list":
                cmd_list(client)
            elif args.command == "delete":
                cmd_delete(client, args.id)
            elif args.command == "ask":
                cmd_ask(client, args.question)
        except httpx.HTTPError as exc:
            _print_error_and_exit(exc)
        except OSError as exc:
            _print_error_and_exit(exc)


if __name__ == "__main__":
    main()
