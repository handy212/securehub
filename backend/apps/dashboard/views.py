"""
Dashboard console views.

Domain logic lives in focused modules; this package re-exports symbols for
``from apps.dashboard import views`` and URL routing compatibility.
"""

from apps.alarms.tasks import (  # noqa: F401 — test patch targets
    send_reactivation_notice,
    send_subscription_lockout_notice,
    send_suspension_notice,
)
from apps.communication.tasks import send_broadcast_push_notifications  # noqa: F401
from apps.dashboard.console_auth import (  # noqa: F401
    CONSOLE_LOGIN_ATTEMPT_LIMIT,
    CONSOLE_LOGIN_LOCKOUT_SECONDS,
    ConsoleLoginView,
)
from apps.dashboard.guarding_asset_console import GuardingAssetsView  # noqa: F401
from apps.dashboard.site_helpers import (  # noqa: F401
    build_active_faults as _build_active_faults,
    visible_console_events as _visible_console_events,
)
from apps.hik_adapter.services import HikPartnerService  # noqa: F401 — test patch targets
from apps.dashboard.views_billing import *  # noqa: F403, F401
from apps.dashboard.views_emergency import *  # noqa: F403, F401
from apps.dashboard.views_guarding import *  # noqa: F403, F401
from apps.dashboard.views_ops import *  # noqa: F403, F401
from apps.dashboard.views_sites import *  # noqa: F403, F401
