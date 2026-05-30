"""Guarding console views — re-export hub for URLs and tests."""

from apps.dashboard.views_guarding_backoffice import *  # noqa: F403, F401
from apps.dashboard.views_guarding_client import *  # noqa: F403, F401
from apps.dashboard.views_guarding_dispatch import *  # noqa: F403, F401
from apps.dashboard.views_guarding_ops import *  # noqa: F403, F401
from apps.dashboard.views_guarding_reports import *  # noqa: F403, F401

