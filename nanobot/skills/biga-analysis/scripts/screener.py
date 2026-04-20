#!/usr/bin/env python3
"""Stable CLI entrypoint for the stock screener skill."""

import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from stock_screener.main import main


if __name__ == "__main__":
    main()
