"""Application entry point for running SusuTurn as a module: python -m susuturn."""

import sys
from susuturn.cli import main

if __name__ == "__main__":
    sys.exit(main())
