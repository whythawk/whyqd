# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.dtypes import ChecksumContent
from whyqd.parsers.datasource import DataSourceParser

if TYPE_CHECKING:
    from whyqd.models import DataSourceModel


class V1ChecksumParser:
    """whyqd 1.x's data checksum: the table as 1.x reads it, printed by pandas, hashed with BLAKE2b-512.

    Its result depends on how pandas prints a table, so it verifies 1.x checksums and makes no new ones. It reads
    with the data source's 1.x settings (`header`, `sheet_name`, `attributes`), as 1.x did.

    Example:
      ```python
      from whyqd.parsers.v1 import V1ChecksumParser

      V1ChecksumParser().checksum(model=datasource.get) == datasource.get.get_checksum("table-1x")
      ```
    """

    def checksum(self, *, model: DataSourceModel) -> str:
        attributes = model.attributes.terms if model.attributes else {}
        derived = DataSourceParser().derive_data_model(
            source=model.path, mimetype=model.mime, sheet_name=model.sheet_name, header=model.header, **attributes
        )
        return derived.get_checksum(ChecksumContent.TABLE_1X)
