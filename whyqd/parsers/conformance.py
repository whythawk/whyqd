# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd
import polars as pl

from whyqd.dtypes import CellType, FieldType, FindingKind, MimeType
from whyqd.models import FieldModel, FindingModel, PolicyModel, ReportModel
from whyqd.parsers.reading import ReadingParser
from whyqd.parsers.row_key import RowKeyParser


@dataclass
class Refused:
    """One source field's refused cells, kept until the actions have run, since only a surviving row can halt."""

    field: str
    cells: pl.Series
    readings: pl.DataFrame
    rows: pl.Series


class ConformanceParser:
    """Make a table conform to its destination schema, or say why it cannot.

    A field with a declared type is read at the source. Every refusal is carried through the actions by the row key, and
    a destination field is then read from whatever the crosswalk built and its constraints checked. A refused cell halts
    only where the crosswalk reads it, in a row that survives. Each run finishes reading first, so one report holds
    everything found, and a transform either has a table that conforms or has none.

    Example:
      ```python
      conformance = ConformanceParser()
      df = conformance.source(table=table, types=types, fields=fields, missing=[], inputs={})
      df = conformance.destination(df=actions(df), fields=destination, missing=[], policies={})
      conformance.report(path=path, mime=mime).findings
      ```
    """

    NOT_READ: ClassVar[frozenset[str]] = frozenset({FieldType.ANY.value, FieldType.ARRAY.value})
    TEXT: ClassVar[str] = FieldType.STRING.value
    PANDAS: ClassVar[dict[str, str]] = {"number": "Float64", "integer": "Int64", "boolean": "boolean", "string": "string"}
    DATES: ClassVar[frozenset[str]] = frozenset(
        {
            FieldType.DATE.value,
            FieldType.DATETIME.value,
            FieldType.USDATE.value,
            FieldType.MONTH.value,
            FieldType.QUARTER.value,
            FieldType.YEAR.value,
        }
    )
    NUMBERS: ClassVar[frozenset[str]] = frozenset({FieldType.NUMBER.value, FieldType.INTEGER.value})
    MAPS_DIRECTLY: ClassVar[frozenset[str]] = frozenset({"RENAME", "SELECT", "SELECT_NEWEST", "SELECT_OLDEST"})
    WARNINGS: ClassVar[dict[str, str]] = {
        "stored-as-other-type": "a workbook stores these as another type, which Excel may have converted on opening; "
        "check them against the file's owner",
        "several-currencies": "the amounts are in several currencies, and read as one number; split them with a crosswalk "
        "action before summing",
        "year-below-1000": "these read as a year before 1000; declare `yy` and `rules.yearStart` if the year is shortened",
        "time-dropped": "a date does not keep a time; use a `datetime` field if it matters",
        "repeated-hour": "the clocks went back, so these read as the earlier time; check them if the hour matters",
        "unread-refusal": "no action reads this field, so it does not stop the transform; correct its declaration or "
        "remove it",
    }

    def __init__(self) -> None:
        self.reading = ReadingParser()
        self.row_key = RowKeyParser()
        self.refused: list[Refused] = []
        self.conflicted: set[str] = set()
        self.faults: list[FindingModel] = []
        self.warnings: list[FindingModel] = []

    def missing(self, cells: pl.Series, missing: list[str]) -> pl.Series:
        """A cell the schema declares to mean nothing, as an empty one."""
        if not missing:
            return cells
        return cells.zip_with(~cells.is_in(missing).fill_null(False), pl.repeat(None, cells.len(), eager=True, dtype=pl.String))

    def is_declared(self, field: FieldModel) -> bool:
        return field.dtype not in (self.TEXT, *self.NOT_READ) or field.policy is not None

    def source(
        self,
        *,
        table: pl.DataFrame,
        types: pl.DataFrame,
        fields: list[FieldModel],
        missing: list[str],
        inputs: dict[str, str],
    ) -> pd.DataFrame:
        """The table for the actions: each declared field read, the rest kept as text. `inputs` names an undeclared field
        an action reads as a type, whose refusals are recorded and whose text is left for that action."""
        df = table.to_pandas()
        rows = table[self.row_key.ROW]
        for field in fields:
            if field.name not in table.columns:
                continue
            cells = self.missing(table[field.name].alias(self.reading.CELL), missing)
            tags = types[field.name] if field.name in types.columns else None
            if self.is_declared(field) and field.dtype not in self.NOT_READ:
                read = self.reading.column(cells=cells, dtype=field.dtype, policy=field.policy, types=tags)
                self.keep(field=field.name, cells=cells, readings=read, rows=rows, policy=field.policy, types=tags)
                df[field.name] = self.pandas(read["value"], field.dtype, df.index)
                continue
            df[field.name] = cells.to_pandas().astype(self.PANDAS[self.TEXT]).set_axis(df.index).astype(object).where(
                cells.is_not_null().to_numpy(), None
            )
            if tags is not None:
                self.warn_stored(field=field.name, types=tags, rows=rows)
            if field.name in inputs:
                read = self.reading.column(cells=cells, dtype=inputs[field.name], types=tags)
                self.keep(field=field.name, cells=cells, readings=read, rows=rows)
        return df

    def pandas(self, value: pl.Series, dtype: str, index: pd.Index) -> pd.Series:
        """A read column for the pandas frame, an interim until the actions are written in Polars."""
        if nullable := self.PANDAS.get(dtype):
            return pd.Series(value.to_list(), dtype=nullable if value.dtype != pl.Decimal else object, index=index)
        return pd.Series(value.to_pandas().to_numpy(), index=index)

    def keep(
        self,
        *,
        field: str,
        cells: pl.Series,
        readings: pl.DataFrame,
        rows: pl.Series,
        policy: PolicyModel | None = None,
        types: pl.Series | None = None,
    ) -> None:
        """Hold a field's refusals until the rows that survive are known, and report what warns."""
        self.refused.append(Refused(field=field, cells=cells, readings=readings, rows=rows))
        self.warn_cells(field=field, readings=readings, cells=cells, rows=rows)
        if policy is not None:
            counts = self.reading.currencies(cells=cells, policy=policy)
            if sum(1 for count in counts.values() if count) > 1:
                detail = ", ".join(f"`{mark}`: {count}" for mark, count in counts.items() if count)
                self.warn(code="several-currencies", field=field, says=detail, count=sum(counts.values()), first=None)

    def warn(self, *, code: str, field: str, says: str, count: int, first: int | None) -> None:
        where = "" if first is None else f", first at row {first}"
        self.warnings.append(
            FindingModel(
                code=code,
                kind=FindingKind.WARNING,
                message=f"Field `{field}`: {says}{where}: {self.WARNINGS[code]}.",
                rows=[] if first is None else [first],
                field=field,
                count=count,
            )
        )

    def warn_stored(self, *, field: str, types: pl.Series, rows: pl.Series) -> None:
        stored = self.reading.stored_types(types)
        if stored:
            first = rows.filter(types.is_in(list(stored)).fill_null(False)).min()
            says = ", ".join(f"{count} {CellType(tag).name.lower()} cells" for tag, count in stored.items())
            self.warn(code="stored-as-other-type", field=field, says=says, count=sum(stored.values()), first=first)

    def warn_cells(self, *, field: str, readings: pl.DataFrame, cells: pl.Series, rows: pl.Series) -> None:
        warned = readings["warning"]
        for code in warned.drop_nulls().unique().sort().to_list():
            mask = (warned == code).fill_null(False)
            self.warn(code=code, field=field, says=f"{mask.sum()} cells", count=mask.sum(), first=rows.filter(mask).min())

    def settle_source(self, *, df: pd.DataFrame, read_fields: set[str]) -> None:
        """Turn the source's refusals into findings: a surviving row in a field the crosswalk reads is a fault, and an
        unread field only warns."""
        surviving = pl.Series(self.row_key.ROW, pd.to_numeric(df[self.row_key.ROW]).to_numpy(), dtype=pl.UInt32)
        for refused in self.refused:
            kept = refused.rows.is_in(surviving.implode().explode()).fill_null(False)
            readings = refused.readings.filter(kept)
            if readings["reason"].null_count() == readings.height:
                continue
            found = self.reading.findings(
                field=refused.field,
                cells=refused.cells.filter(kept),
                readings=readings,
                rows=refused.rows.filter(kept).cast(pl.Int64),
            )
            if refused.field in read_fields:
                self.faults += found
            else:
                count = readings["reason"].drop_nulls().len()
                self.warn(code="unread-refusal", field=refused.field, says=f"{count} cells refused", count=count, first=None)
        self.refused = []

    def as_cells(self, column: pd.Series) -> tuple[pl.Series, pl.Series]:
        """A built column as a reader takes it: each value's text, and whether it is a stored value already."""
        texts, tags = [], []
        for value in column.astype(object).tolist():
            if value is None or value is pd.NA or (isinstance(value, float) and value != value) or value is pd.NaT:
                texts.append(None)
                tags.append(CellType.STRING.value)
            elif isinstance(value, bool):
                texts.append("TRUE" if value else "FALSE")
                tags.append(CellType.BOOLEAN.value)
            elif isinstance(value, (int, float)) or type(value).__name__ == "Decimal":
                texts.append(repr(float(value)) if isinstance(value, float) else str(value))
                tags.append(CellType.NUMBER.value)
            elif hasattr(value, "isoformat") and not isinstance(value, str):
                midnight = isinstance(value, pd.Timestamp) and value == value.normalize()
                texts.append(value.date().isoformat() if midnight else value.isoformat())
                tags.append(CellType.DATE.value)
            else:
                texts.append(str(value))
                tags.append(CellType.STRING.value)
        return pl.Series(self.reading.CELL, texts, dtype=pl.String), pl.Series(self.reading.CELL, tags, dtype=pl.String)

    def as_list(self, value) -> list | None:
        """An array's value, from a list or the literal a saved file holds, each item as text."""
        if isinstance(value, str):
            value = ast.literal_eval(value)
        if value is None or not len(value):
            return None
        return [None if pd.isna(item) else self.as_item(item) for item in value]

    def as_item(self, item) -> str:
        """An array's item as text: a date read at the source as its date alone, as a date cell renders."""
        if isinstance(item, pd.Timestamp) and item == item.normalize():
            return item.date().isoformat()
        return str(item).strip()

    def is_typed_as(self, column: pd.Series, dtype: str) -> bool:
        """Whether a built column already holds its destination type, so it is passed on as it is."""
        kind = str(column.dtype).lower()
        if dtype == FieldType.NUMBER.value:
            return kind in ("float64", "float32")
        if dtype == FieldType.BOOLEAN.value:
            return kind == "boolean"
        if dtype == FieldType.DATE.value:
            values = column.dropna()
            return "datetime64" in kind and "," not in kind and (values == values.dt.normalize()).all()
        if dtype == FieldType.DATETIME.value:
            return "datetime64" in kind
        if dtype == FieldType.TIME.value:
            return kind == "object" and column.dropna().map(lambda v: type(v).__name__ == "time").all() and column.notna().any()
        if dtype == FieldType.DURATION.value:
            return "timedelta" in kind
        return False

    def destination(
        self, *, df: pd.DataFrame, fields: list[FieldModel], missing: list[str], policies: dict[str, PolicyModel]
    ) -> pd.DataFrame:
        """Read each destination field from what the crosswalk built, and check what it declares. `policies` holds the
        reading of text an action built."""
        rows = pl.Series(self.row_key.ROW, pd.to_numeric(df[self.row_key.ROW]).to_numpy(), dtype=pl.Int64)
        for field in fields:
            if field.name not in df.columns or field.name in self.conflicted:
                continue
            column = df[field.name]
            if field.dtype in self.NOT_READ:
                if field.dtype == FieldType.ARRAY.value:
                    df[field.name] = pd.Series([self.as_list(value) for value in column.tolist()], index=df.index, dtype=object)
                self.check_constraints(field=field, column=df[field.name], rows=rows)
                continue
            if self.is_typed_as(column, field.dtype):
                self.check_constraints(field=field, column=column, rows=rows)
                continue
            cells, tags = self.as_cells(column)
            cells = self.missing(cells, missing)
            policy = policies.get(field.name) or field.policy
            read = self.reading.column(cells=cells, dtype=field.dtype, policy=policy, types=tags)
            self.warn_cells(field=field.name, readings=read, cells=cells, rows=rows)
            self.faults += self.reading.findings(field=field.name, cells=cells, readings=read, rows=rows)
            # A text field keeps a whitespace-only cell as written, though it counts as blank when a value is required
            value = cells if field.dtype == self.TEXT else read["value"]
            df[field.name] = self.pandas(value, field.dtype, df.index)
            self.check_constraints(field=field, column=df[field.name], rows=rows, skip=read["kind"] == "refused")
        return df

    def check_constraints(
        self, *, field: FieldModel, column: pd.Series, rows: pl.Series, skip: pl.Series | None = None
    ) -> None:
        """Check each constraint the field applies. A refused cell has already been reported, so it is not counted again.
        An unmapped category term is not yet checked, since whyqd cannot yet say what to do with one."""
        limits = field.constraints
        if limits is None:
            return
        kept = pd.Series(True, index=column.index) if skip is None else pd.Series(~skip.to_numpy(), index=column.index)
        blank = column.isna()
        if field.dtype == self.TEXT:
            blank = blank | (column.astype("string").str.strip() == "").fillna(False)
        failures = {}
        if limits.required:
            failures["constraint-required"] = (blank & kept, "holds nothing, and is required")
        if limits.unique:
            duplicated = column.duplicated(keep=False) & ~blank
            failures["constraint-unique"] = (duplicated & kept, "repeats a value, and must be unique")
        numeric = pd.api.types.is_numeric_dtype(column) and not pd.api.types.is_bool_dtype(column)
        if numeric and limits.minimum is not None:
            failures["constraint-minimum"] = ((column < limits.minimum).fillna(False) & kept, f"is below {limits.minimum}")
        if numeric and limits.maximum is not None:
            failures["constraint-maximum"] = ((column > limits.maximum).fillna(False) & kept, f"is above {limits.maximum}")
        if field.dtype == self.TEXT:
            lengths = column.astype("string").str.len()
            if limits.minLength is not None:
                failures["constraint-min-length"] = ((lengths < limits.minLength).fillna(False) & kept, f"has under {limits.minLength} characters")
            if limits.maxLength is not None:
                failures["constraint-max-length"] = ((lengths > limits.maxLength).fillna(False) & kept, f"has over {limits.maxLength} characters")
        for code, (failed, says) in failures.items():
            count = int(failed.sum())
            if count:
                first = rows.filter(pl.Series(failed.to_numpy().astype(bool))).min()
                self.faults.append(
                    FindingModel(
                        code=code,
                        kind=FindingKind.FAULT,
                        message=f"Field `{field.name}`: {count} cells, first at row {first}, each {says}. Next, loosen "
                        "the constraint, or decide about the source.",
                        rows=[first],
                        field=field.name,
                        count=count,
                        setting=f"constraints of `{field.name}`",
                    )
                )

    def conflict(self, *, source: FieldModel, destination: FieldModel) -> None:
        """A source field declared as one type and mapped to another that cannot hold it, found with no cell read."""
        declared, wanted = source.dtype, destination.dtype
        if declared in (self.TEXT, *self.NOT_READ) or wanted in (self.TEXT, *self.NOT_READ) or declared == wanted:
            return
        if {declared, wanted} <= self.DATES or {declared, wanted} <= self.NUMBERS:
            return
        self.conflicted.add(destination.name)
        self.faults.append(
            FindingModel(
                code="type-conflict",
                kind=FindingKind.FAULT,
                message=f"Source field `{source.name}` is `{declared}`, and the crosswalk maps it to `{destination.name}`, "
                f"which is `{wanted}`. Next, change one of the two types.",
                field=source.name,
                setting=f"type of `{source.name}`",
            )
        )

    def report(self, *, path: str, mime: MimeType) -> ReportModel:
        """Everything a run found, what halts it first."""
        return ReportModel(path=path, mime=mime, place="row", findings=[*self.faults, *self.warnings])
