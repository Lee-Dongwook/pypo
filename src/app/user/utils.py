from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import cast

import dns.asyncresolver
import dns.exception
import dns.resolver
from dns.rdtypes.ANY.MX import MX

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

