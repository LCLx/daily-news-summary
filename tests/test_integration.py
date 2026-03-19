#!/usr/bin/env python3
"""
Integration test: runs the full email pipeline end-to-end.
Equivalent to manually triggering the GitHub Actions workflow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipelines.email_pipeline import main

if __name__ == '__main__':
    main()
