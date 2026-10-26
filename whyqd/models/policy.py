# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class NumberFormatModel(BaseModel):
    """How a number is written: the number format of a CSV on the Web derived datatype
    ([Metadata Vocabulary for Tabular Data, section 5.11.2](https://www.w3.org/TR/tabular-metadata/#derived-datatypes))."""

    decimalChar: Optional[str] = Field(None, description="The decimal mark, such as `.` or `,`.")
    groupChar: Optional[str] = Field(None, description="The grouping mark, such as `,` in `1,000`.")
    pattern: Optional[str] = Field(None, description="A number pattern, such as `#,##0.00`.")
    model_config = ConfigDict(validate_assignment=True)


class PolicyModel(BaseModel):
    """How to read a field's text as its type: a CSV on the Web derived datatype
    ([Metadata Vocabulary for Tabular Data, section 5.11.2](https://www.w3.org/TR/tabular-metadata/#derived-datatypes)),
    `base` and `format`, with whyqd's own `rules` beside it.

    A field without a policy is read as text.
    """

    base: Optional[str] = Field(None, description="The datatype the text is read as, such as `decimal` or `date`.")
    format: Optional[Union[str, NumberFormatModel]] = Field(
        None,
        description="How the text is written: a number's format; a boolean's `true|false` pair, such as `Y|N`; or a "
        "date's pattern, such as `dd.MM.yyyy`.",
    )
    rules: dict[str, Any] = Field({}, description="whyqd's own reading rules, beyond what `base` and `format` say.")
    model_config = ConfigDict(validate_assignment=True)
