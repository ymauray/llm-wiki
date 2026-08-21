"""
LLM Wiki Application Entry Point

Based strictly on Andrej Karpathy's LLM Wiki Spec.

Usage:
  python app.py                    # Starts interactive menu mode
  python app.py ingest             # Ingests new sources from /sources
  python app.py query "Question"   # Queries wiki and synthesizes answer
  python app.py lint               # Runs wiki health check
  python app.py status             # Shows stats and recent activity log
"""

from cli import main

if __name__ == "__main__":
    main()
