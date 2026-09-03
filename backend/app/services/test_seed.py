"""Compatibility import for the development/test seed.

The canonical seed implementation lives in ``app.bootstrap.test_seed``.
This module remains only for established scripts and test imports.
"""

from app.bootstrap.test_seed import seed_test_data

__all__ = ["seed_test_data"]
