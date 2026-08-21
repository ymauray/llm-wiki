"""
CLI Module for LLM Wiki

Provides command-line argument parsing and interactive shell interface.
Supports:
- ingest : Process new source files in /sources
- query  : Ask a question against the wiki
- lint   : Perform structural and semantic health check
- status : Show wiki stats and recent log entries
"""

import sys
import argparse
from typing import Optional
from config import SOURCES_DIR, WIKI_DIR, LITELLM_PROXY_API_BASE, LITELLM_PROXY_API_KEY
from wiki_manager import (
    ingest_new_sources,
    query_wiki,
    save_synthesis_to_wiki,
    lint_wiki,
    get_wiki_status,
    reset_wiki,
)


def print_banner():
    print("=" * 60)
    print(" 🧠 LLM Wiki - Persistent Knowledge Base Maintainer")
    print(" Based on Andrej Karpathy's LLM Wiki Spec")
    print(" Model: strictly 'llm' via LiteLLM Proxy")
    print("=" * 60)


def check_environment_credentials():
    """Validates presence of required environment variables."""
    base = LITELLM_PROXY_API_BASE
    key = LITELLM_PROXY_API_KEY
    
    if not base or not key:
        print("\n⚠️  WARNING: Mandatory environment variables are missing!")
        print("   - LITELLM_PROXY_API_BASE: " + (base if base else "NOT SET"))
        print("   - LITELLM_PROXY_API_KEY:  " + ("******" if key else "NOT SET"))
        print("\nPlease set them in your environment or in a '.env' file:")
        print("   export LITELLM_PROXY_API_BASE='http://localhost:4000'")
        print("   export LITELLM_PROXY_API_KEY='sk-123456'\n")


def handle_ingest():
    """Handles the source ingestion workflow."""
    print("\n🚀 Running Ingestion on /sources ...")
    ingested = ingest_new_sources()
    if ingested:
        print(f"\n✨ Ingestion complete. Ingested {len(ingested)} source(s):")
        for title in ingested:
            print(f"   - {title}")
    else:
        print("\nℹ️  No new or modified sources to ingest.")


def handle_query(query_text: str):
    """Handles querying the wiki."""
    print(f"\n🔍 Querying Wiki: \"{query_text}\" ...")
    answer, relevant_files = query_wiki(query_text)
    
    print("\n" + "=" * 60)
    print("💡 LLM Wiki Answer:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

    if relevant_files:
        print(f"\n📚 Referenced Wiki Pages: {', '.join(relevant_files)}")

    # Prompt user to save synthesis back into wiki (Compounding Knowledge pattern)
    print("\n💾 Would you like to file this answer back into the Wiki as a persistent page?")
    choice = input("   Save as synthesis page? [y/N]: ").strip().lower()
    if choice in ["y", "yes"]:
        default_title = query_text[:40].strip()
        title_input = input(f"   Enter page title [{default_title}]: ").strip()
        title = title_input if title_input else default_title
        saved_file = save_synthesis_to_wiki(title, answer)
        print(f"   ✅ Saved to wiki page: wiki/{saved_file}")


def handle_lint():
    """Handles linting the wiki."""
    print("\n🧹 Running Wiki Lint & Health Check ...")
    report = lint_wiki()
    print("\n" + report)


def handle_status():
    """Displays current wiki status and activity log."""
    stats = get_wiki_status()
    print("\n📊 LLM Wiki Status:")
    print(f"   • Raw Sources directory: {SOURCES_DIR}")
    print(f"   • Wiki Pages directory:  {WIKI_DIR}")
    print(f"   • Total Sources Ingested: {stats['sources_count']}")
    print(f"   • Total Wiki Pages:      {stats['wiki_pages_count']}")
    print(f"   • Index File (index.md): {'Exists' if stats['has_index'] else 'Missing'}")
    print(f"   • Activity Log (log.md): {'Exists' if stats['has_log'] else 'Missing'}")
    
    print("\n📜 Recent Activity Log (from log.md):")
    if stats["last_log_entries"]:
        for entry in stats["last_log_entries"]:
            print(f"   {entry}")
    else:
        print("   (No log entries yet)")
    print()


def handle_reset(hard: bool = False):
    """Handles resetting the wiki."""
    print("\n⚠️  Wiping Wiki pages, index, log, and ingestion manifest...")
    if hard:
        print("   (Hard reset: clearing /sources directory as well)")
    
    reset_wiki(keep_sources=not hard)
    print("✅ Wiki reset successfully! Ready for a fresh start.")


def run_interactive_mode():
    """Runs interactive menu loop."""
    print_banner()
    check_environment_credentials()

    while True:
        print("\nMain Menu:")
        print("  [1] Ingest new sources from /sources")
        print("  [2] Query Wiki")
        print("  [3] Lint Wiki / Health Check")
        print("  [4] View Wiki Status & Log")
        print("  [5] Reset Wiki (dev mode)")
        print("  [6] Exit")

        choice = input("\nSelect an option [1-6]: ").strip()

        if choice == "1":
            handle_ingest()
        elif choice == "2":
            query_input = input("\nEnter your question or prompt: ").strip()
            if query_input:
                handle_query(query_input)
        elif choice == "3":
            handle_lint()
        elif choice == "4":
            handle_status()
        elif choice == "5":
            confirm = input("⚠️ Are you sure you want to reset the wiki? [y/N]: ").strip().lower()
            if confirm in ["y", "yes"]:
                handle_reset()
        elif choice in ["6", "q", "exit", "quit"]:
            print("\n👋 Exiting LLM Wiki. Goodbye!\n")
            sys.exit(0)
        else:
            print("❌ Invalid selection, please enter a number from 1 to 6.")


def handle_web(host: str = "0.0.0.0", port: int = 5000):
    """Launches the Flask Web Application."""
    from web_app import run_server
    run_server(host=host, port=port)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Wiki - Incremental persistent knowledge base maintainer powered by LiteLLM."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: web
    web_parser = subparsers.add_parser("web", help="Start the Web Application (ChatGPT/Gemini style UI)")
    web_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0 - all interfaces)")
    web_parser.add_argument("--port", type=int, default=5000, help="Port number (default: 5000)")

    # Command: ingest
    subparsers.add_parser("ingest", help="Ingest new raw source documents from /sources")

    # Command: query
    query_parser = subparsers.add_parser("query", help="Query the wiki and synthesize answers")
    query_parser.add_argument("prompt", type=str, nargs="?", help="Question or prompt to ask the wiki")

    # Command: lint
    subparsers.add_parser("lint", help="Perform structural and semantic health check on wiki")

    # Command: status
    subparsers.add_parser("status", help="Show current wiki stats and recent activity log")

    # Command: reset
    reset_parser = subparsers.add_parser("reset", help="Reset wiki pages, manifest, index, and log to start from scratch")
    reset_parser.add_argument("--hard", action="store_true", help="Also clear files in /sources")

    # Command: interactive
    subparsers.add_parser("interactive", help="Start interactive CLI shell")

    args = parser.parse_args()

    check_environment_credentials()

    if args.command == "web":
        handle_web(host=args.host, port=args.port)
    elif args.command == "ingest":
        handle_ingest()
    elif args.command == "query":
        if args.prompt:
            handle_query(args.prompt)
        else:
            query_input = input("Enter query: ").strip()
            if query_input:
                handle_query(query_input)
    elif args.command == "lint":
        handle_lint()
    elif args.command == "status":
        handle_status()
    elif args.command == "reset":
        handle_reset(hard=args.hard)
    elif args.command == "interactive":
        run_interactive_mode()
    else:
        # Default behavior: Launch Web Application
        handle_web()


