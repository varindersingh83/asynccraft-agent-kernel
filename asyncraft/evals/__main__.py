"""CLI entry point for eval harness."""

import sys
import asyncio
from asynccraft.evals.runner import run_evals


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "run":
        print("Usage: python -m asynccraft.evals run")
        sys.exit(1)
    
    asyncio.run(run_evals())


if __name__ == "__main__":
    main()
