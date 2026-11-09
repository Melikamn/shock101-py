"""Command-line entry point for ``python -m echo_lite``."""

import sys

from echo_lite.agent import run


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:])))
