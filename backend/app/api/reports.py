"""Compatibility alias for the reports HTTP adapter.

The alias keeps the historical ``app.api.reports`` test-injection seam while
leaving the router implementation owned by the reports module.
"""

import sys

from app.modules.reports.api import reports as _reports_api

sys.modules[__name__] = _reports_api
