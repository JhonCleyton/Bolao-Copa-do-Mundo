"""
Timezone utility for Brasilia time (UTC-3)

The match_date values in the database are stored in Brasilia time (UTC-3),
so all comparisons must use Brasilia time instead of UTC.
"""

from datetime import datetime, timedelta, timezone

# Brasilia timezone (UTC-3)
BRASILIA_TZ = timezone(timedelta(hours=-3))


def get_brasilia_now() -> datetime:
    """
    Get current datetime in Brasilia timezone (UTC-3) as a naive datetime.
    Use this instead of datetime.utcnow() when comparing with match_date.
    """
    return datetime.now(BRASILIA_TZ).replace(tzinfo=None)
