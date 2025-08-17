#!/usr/bin/env python3
"""Simple synapse CLI wrapper that avoids complex imports."""

import sys
import subprocess

if __name__ == "__main__":
    # Basic commands that don't require complex imports
    if len(sys.argv) < 2:
        print("Usage: synapse_simple.py <command>")
        print("Available commands: discover, parse, ingest")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "discover":
        from graph_rag.cli.commands.discover import discover_command
        discover_command()
    elif command == "version":
        print("Synapse GraphRAG v0.1.0")
    elif command == "help":
        print("Synapse GraphRAG - Simple CLI")
        print("Commands:")
        print("  discover  - Discover files")
        print("  version   - Show version")
        print("  help      - Show this help")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)