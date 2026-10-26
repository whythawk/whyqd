# SPDX-License-Identifier: BSD-3-Clause
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


class UtcParser:
    """Times whyqd records about itself: aware, in UTC, written with `Z`.

    A naive time is read as UTC, since 1.x wrote its times naive in UTC; a time in another zone is converted.

    Example:
      ```python
      from whyqd.models.utc import UtcParser

      UtcParser().now()  # datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
      ```
    """

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def read(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


UtcTime = Annotated[datetime, AfterValidator(UtcParser().read)]
