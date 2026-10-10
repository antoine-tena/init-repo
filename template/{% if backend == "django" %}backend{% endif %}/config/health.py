"""Vérifications de la sonde de disponibilité ([SANTE])."""

import structlog
from django.db import DatabaseError, connection

logger = structlog.get_logger(__name__)


def is_database_reachable() -> bool:
    try:
        connection.ensure_connection()
    except DatabaseError:
        logger.warning("health.database_unreachable")
        return False
    return True
