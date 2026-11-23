# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from datetime import datetime, timedelta
from typing import ClassVar

import polars as pl

from whyqd.config.names import NameTables
from whyqd.dtypes import CellType, FieldFamilies, FieldType, ReadingWarning, RefusalReason, SerialDate
from whyqd.models import PolicyModel, RulesModel
from whyqd.reading.pattern import PatternParser
from whyqd.reading.reader import BaseReadingParser


class DateParser(BaseReadingParser):
    """Read a date, time, datetime, month, quarter, or year field's cells by its declared patterns, or with none its
    canonical form."""

    # A type's canonical patterns, which also read a stored cell's rendering, as `CellType.describe` states it
    CANONICAL: ClassVar[dict[str, list[str]]] = {
        "date": ["yyyy-MM-dd"],
        "time": ["HH:mm:ss", "HH:mm:ss.S", "HH:mm"],
        "datetime": [
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ss.S",
            "yyyy-MM-dd'T'HH:mm",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd HH:mm:ss.S",
            "yyyy-MM-dd HH:mm",
        ],
        "month": ["yyyy-MM"],
        "quarter": ["yyyy-MM"],
        "year": ["yyyy"],
    }
    # A period names no day, and a year no month, so its date is first read at the period's start
    DEFAULTS: ClassVar[dict[str, str]] = {"M": "1", "d": "1"}
    QUARTER_MONTHS: ClassVar[int] = 3
    HALF_DAY: ClassVar[int] = 12
    NO_HOUR: ClassVar[str] = "99"
    EPOCH_1900: ClassVar[datetime] = datetime(1899, 12, 30)
    EPOCH_1900_EARLY: ClassVar[datetime] = datetime(1899, 12, 31)
    EPOCH_1904: ClassVar[datetime] = datetime(1904, 1, 1)
    EPOCH_UNIX: ClassVar[datetime] = datetime(1970, 1, 1)
    PHANTOM_LEAP_DAY: ClassVar[int] = 60
    LAST_SERIAL_1900: ClassVar[int] = 2_958_465
    LAST_SERIAL_1904: ClassVar[int] = 2_957_003
    MILLISECONDS_A_DAY: ClassVar[int] = 86_400_000
    EARLY_YEAR: ClassVar[int] = 1000
    UTC: ClassVar[str] = "UTC"
    STORED_DATETIME_MIDNIGHT: ClassVar[str] = "yyyy-MM-dd"
    # Each type's text for Polars to check, once the declared rules have read a cell: never Polars' own `%y` or `%b`,
    # which take a fixed century and the machine's month names
    ISO: ClassVar[dict[str, tuple[str, str, str]]] = {
        "date": ("{}-{}-{}", "yMd", "%Y-%m-%d"),
        "time": ("{}:{}:{}.{}", "HmsS", "%H:%M:%S%.f"),
        "datetime": ("{}-{}-{} {}:{}:{}.{}", "yMdHmsS", "%Y-%m-%d %H:%M:%S%.f"),
    }
    YEAR_WIDTH: ClassVar[int] = 4
    FIELD_WIDTH: ClassVar[int] = 2
    MICROSECONDS: ClassVar[dict[str, int]] = {"d": 86_400_000_000, "H": 3_600_000_000, "m": 60_000_000, "s": 1_000_000}

    def __init__(self) -> None:
        super().__init__()
        self.pattern = PatternParser()

    def pattern_regex(
        self, pattern: str, rules: RulesModel, *, quantities: bool = False, tail: bool = False
    ) -> tuple[str, list[str]]:
        """A declared pattern as a regular expression capturing each field, and those fields in order. A number's width
        says nothing of its meaning, so `dd` reads `1`, unless digits run together, as in `yyyyMMdd`. On a duration the
        first field is a quantity of any length: `H:mm` reads `100:30`. With `tail`, a date's cell may also hold a time."""
        p, regex, fields = self.patterns, [], []
        written = self.pattern.parts(self.normalised(pattern))
        for index, (is_field, text) in enumerate(written):
            if not is_field:
                regex.append(p.literal(text))
                continue
            beside = [written[i][0] for i in (index - 1, index + 1) if 0 <= i < len(written)]
            if text in ("MMM", "MMMM"):
                captured = p.names(list(self.month_names(rules)))
            elif text[0] == "E":
                captured = p.names(self.weekday_names(rules))
            elif text == "a":
                captured = p.names(list(self.day_period_names(rules)))
            elif (quantities and not fields) or text == "S":
                captured = "[0-9]+"
            elif any(beside):
                captured = f"[0-9]{{{4 if text[0] == 'y' and len(text) != 2 else len(text)}}}"
            else:
                low, high = self.pattern.WIDTHS[text]
                captured = f"[0-9]{{{low},{high}}}"
            regex.append(f"({captured})")
            fields.append(text)
        return "^" + "".join(regex) + (p.TIME_TAIL if tail else "") + "$", fields

    def name_key(self, name: str) -> str:
        """A name as a cell's may be compared with it: without case or a closing `.`."""
        return self.normalised(name).lower().rstrip(".")

    def month_names(self, rules: RulesModel) -> dict[str, str]:
        """Every spelling a field reads for a month, with the month's number."""
        table = NameTables.language(rules.language) if rules.language else None
        names = {}
        for index, entries in enumerate(table["months"] if table else []):
            names |= {self.name_key(entry): f"{index + 1:02d}" for entry in entries}
        for index, entry in enumerate(rules.monthNames):
            names |= {
                self.name_key(name): f"{index + 1:02d}" for name in ([entry] if isinstance(entry, str) else entry)
            }
        return names

    def weekday_names(self, rules: RulesModel) -> list[str]:
        return [self.name_key(name) for name in NameTables.language(rules.language)["weekdays"]]

    def period_key(self, name: str) -> str:
        """A day period as a cell's may be compared with it: without case, dots, or spaces, so `p. m.` is `pm`."""
        return "".join(char for char in self.normalised(name).lower() if char != "." and not char.isspace())

    def day_period_names(self, rules: RulesModel) -> dict[str, bool]:
        """Every spelling a field reads for a day period, with whether it is the afternoon: `AM` and `PM` always."""
        table = NameTables.language(rules.language) if rules.language else None
        spelled = {"am": False, "a.m.": False, "pm": True, "p.m.": True}
        for afternoon, key in ((False, "morning"), (True, "afternoon")):
            spelled |= {self.normalised(name).lower(): afternoon for name in (table[key] if table else [])}
        for afternoon, entry in zip((False, True), rules.dayPeriods):
            spelled |= {
                self.normalised(name).lower(): afternoon for name in ([entry] if isinstance(entry, str) else entry)
            }
        return spelled | {self.period_key(name): afternoon for name, afternoon in spelled.items()}

    def pattern_value(
        self, *, text: pl.Series, pattern: str, rules: RulesModel, dtype: str, tail: bool = False
    ) -> tuple[pl.Series, pl.Series]:
        """Whether each cell fits `pattern`, and its value, null for a cell that fits and names no such date."""
        regex, fields = self.pattern_regex(pattern, rules, tail=tail)
        found = text.str.extract_groups(regex).struct.unnest()
        parts = {}
        for index, field in enumerate(fields):
            column = found[str(index + 1)].alias(self.CELL)
            if field in ("MMM", "MMMM"):
                keys = column.str.to_lowercase().str.replace(self.patterns.TRAILING_DOT, "")
                column = keys.replace_strict(self.month_names(rules), default=None, return_dtype=pl.String)
            if field == "yy":
                column = (rules.yearStart + ((column.cast(pl.Int64) - rules.yearStart) % 100)).cast(pl.String)
            parts[field[0]] = column
        if "Q" in parts:
            parts["M"] = (parts["Q"].cast(pl.Int64) * self.QUARTER_MONTHS - (self.QUARTER_MONTHS - 1)).cast(pl.String)
        if "h" in parts:
            parts["H"] = self.twenty_four_hour(hours=parts["h"], periods=parts["a"], rules=rules)
        written, letters, form = self.ISO[dtype]
        frame = pl.DataFrame(
            {
                letter: parts.get(letter, pl.repeat(self.DEFAULTS.get(letter, "0"), text.len(), eager=True))
                for letter in letters
            }
        )
        widths = {"y": self.YEAR_WIDTH, "S": 1}
        columns = [pl.col(letter).str.zfill(widths.get(letter, self.FIELD_WIDTH)) for letter in letters]
        joined = frame.select(pl.format(written, *columns).alias(self.CELL))[self.CELL]
        if dtype == FieldType.DATE.value:
            value = joined.str.to_date(form, strict=False)
        elif dtype == FieldType.TIME.value:
            value = joined.str.to_time(form, strict=False)
        else:
            value = joined.str.to_datetime(form, strict=False, time_unit="us")
        return found["1"].is_not_null().alias(self.CELL), value.alias(self.CELL)

    def twenty_four_hour(self, *, hours: pl.Series, periods: pl.Series, rules: RulesModel) -> pl.Series:
        """A 12-hour clock's hour and day period as a 24-hour hour; one outside 1 to 12 reads as no such time."""
        hour = hours.cast(pl.Int64)
        keys = periods.str.to_lowercase().str.replace_all(self.patterns.DOT_OR_SPACE, "")
        afternoon = keys.replace_strict(self.day_period_names(rules), default=False, return_dtype=pl.Boolean)
        written = (hour % self.HALF_DAY + afternoon.cast(pl.Int64) * self.HALF_DAY).cast(pl.String)
        valid = ((hour >= 1) & (hour <= self.HALF_DAY)).fill_null(False)
        return written.zip_with(valid, pl.repeat(self.NO_HOUR, hours.len(), eager=True))

    def period_end(self, value: pl.Series, dtype: str) -> pl.Series:
        """A month, quarter, or year as the date it ends on, as its `FieldType` states."""
        if dtype == FieldType.MONTH.value:
            return value.dt.month_end()
        every = {FieldType.QUARTER.value: "1q", FieldType.YEAR.value: "1y"}[dtype]
        return value.dt.truncate(every).dt.offset_by(every).dt.offset_by("-1d")

    def read_temporal(self, *, dtype: str, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A date, time, datetime, or period by its declared patterns, or with none its canonical form. A stored date
        cell is already a value, so it reads by its rendering, or by the pattern `rules.cellFormats` gives that
        rendering. A period reads as the date it ends on. A datetime's own offset is read wherever a cell has one, and
        `rules.zone` states the zone of a clock that has none. What is read with something worth checking warns."""
        rules = policy.rules or RulesModel()
        declared = [policy.format] * isinstance(policy.format, str) + rules.alternateFormats
        declared = [self.pattern.standard_pattern(pattern, dtype) for pattern in declared]
        text, mixed = self.digits(self.steps(cells))
        offsets = None
        if dtype == FieldType.DATETIME.value:
            found = text.str.extract_groups(self.patterns.OFFSET).struct.unnest()
            stated = found["2"].alias(self.CELL)
            text = found["1"].alias(self.CELL).zip_with(stated.is_not_null(), text)
            offsets = stated if stated.is_not_null().any() or rules.zone else None
        period = dtype in FieldFamilies.PERIODS
        parsed = FieldType.DATE.value if period else dtype
        read = self.patterns_read(text=text, patterns=declared or self.CANONICAL[dtype], rules=rules, dtype=parsed)
        warned = {}
        if dtype == FieldType.DATE.value and not declared:
            read, warned = self.undeclared_dates(text=text, read=read, rules=rules)
        is_stored = types == CellType.DATE.value
        if is_stored.any():
            stored = rules.cellFormats.get(CellType.DATE)
            patterns = [self.pattern.standard_pattern(stored, dtype)] if stored else self.stored_patterns(dtype)
            rendered = self.patterns_read(text=text, patterns=patterns, rules=rules, dtype=parsed)
            read = tuple(one.zip_with(is_stored, other) for one, other in zip(rendered, read))
            warned = {code: flag & ~is_stored for code, flag in warned.items()}
        fits, twice, value = read
        serial_time = pl.repeat(False, cells.len(), eager=True)
        # A pattern of digits alone, as `yyyyMMdd`, already says what a bare number is
        digits_only = any(all(is_field for is_field, _ in self.pattern.parts(pattern)) for pattern in declared)
        if rules.serial or not (dtype in FieldFamilies.NO_SERIAL or digits_only):
            system = SerialDate(rules.serial or SerialDate.EXCEL_1900)
            fits, value, serial_time, types, serial = self.serials(
                text=text, types=types, fits=fits, value=value, system=system
            )
            if not rules.serial:
                warned[ReadingWarning.SERIAL] = serial
        no_zone = pl.repeat(False, cells.len(), eager=True)
        if dtype in (FieldType.DATE.value, FieldType.DATETIME.value) or period:
            warned[ReadingWarning.YEAR_BELOW_1000] = (value.dt.year() < self.EARLY_YEAR).fill_null(False)
        if dtype == FieldType.DATE.value:
            at_end = text.str.extract(self.patterns.TIME_AT_END, 1)
            warned[ReadingWarning.TIME_DROPPED] = (
                at_end.str.contains(self.patterns.NOT_ZERO).fill_null(False) | serial_time
            )
        if period:
            value = self.period_end(value, dtype).alias(self.CELL)
        if offsets is not None:
            value, warned[ReadingWarning.REPEATED_HOUR], no_zone = self.zoned(
                value=value, offsets=offsets, zone=rules.zone
            )
        frame = self.temporal_frame(
            cells=cells,
            types=types,
            mixed=mixed,
            fits=fits,
            twice=twice,
            named=value.is_not_null() | no_zone,
            no_zone=no_zone,
            warned=warned,
        )
        return self.outcome(frame, value)

    def undeclared_dates(
        self, *, text: pl.Series, read: tuple[pl.Series, pl.Series, pl.Series], rules: RulesModel
    ) -> tuple[tuple[pl.Series, pl.Series, pl.Series], dict[ReadingWarning, pl.Series]]:
        """Read, where a date field declares no pattern, each cell with one reading the canonical form did not: day and
        month as numbers in either order with one separator used twice, `yyyyMMdd`, or a day, a month's name, and a
        year. Two orders reading different days, or a name meaning different months, fit twice. A name reads by
        `rules.language` or `rules.monthNames` where declared, and otherwise wherever it means one month in every
        language whyqd holds."""
        p = self.patterns
        fits, twice, value = read
        order = text.str.extract_groups(p.DATE_ORDER).struct.unnest()
        same = (order["2"] == order["4"]).fill_null(False)
        day_first = self.iso_date(year=order["5"], month=order["3"], day=order["1"])
        month_first = self.iso_date(year=order["5"], month=order["1"], day=order["3"])
        two_days = (day_first != month_first).fill_null(False)
        ordered = day_first.fill_null(month_first)
        run = text.str.extract_groups(p.DATE_RUN).struct.unnest()
        joined = self.iso_date(year=run["1"], month=run["2"], day=run["3"])
        spaced = text.str.replace_all(p.COMMA, " ", literal=True)
        day_name = spaced.str.extract_groups(p.DAY_NAME).struct.unnest()
        name_day = spaced.str.extract_groups(p.NAME_DAY).struct.unnest()
        first = day_name["1"].is_not_null()
        name = day_name["2"].zip_with(first, name_day["1"]).str.to_lowercase().str.replace(p.TRAILING_DOT, "")
        day = day_name["1"].zip_with(first, name_day["2"])
        year = day_name["3"].zip_with(first, name_day["3"])
        declared = rules.language or rules.monthNames
        meanings = (
            {key: {int(month)} for key, month in self.month_names(rules).items()} if declared else NameTables.months()
        )
        present = name.drop_nulls().unique().to_list()
        months = {key: len(meanings.get(self.name_key(key), ())) for key in present}
        month = {key: str(next(iter(meanings[self.name_key(key)]))) for key, count in months.items() if count == 1}
        count = name.replace_strict(months, default=0, return_dtype=pl.Int64).fill_null(0)
        dated = self.iso_date(
            year=year, month=name.replace_strict(month, default=None, return_dtype=pl.String), day=day
        )
        shapes = (
            (order["1"].is_not_null() & same, two_days, ordered, ReadingWarning.DATE_ORDER),
            (run["1"].is_not_null(), None, joined, ReadingWarning.DATE_ORDER),
            (count > 0, count > 1, dated, ReadingWarning.MONTH_NAME),
        )
        nothing = pl.repeat(False, text.len(), eager=True)
        warned = {ReadingWarning.DATE_ORDER: nothing, ReadingWarning.MONTH_NAME: nothing}
        for matched, ambiguous, read_as, code in shapes:
            new = matched.fill_null(False) & ~fits
            if ambiguous is not None:
                twice = twice | (new & ambiguous)
            value = read_as.alias(self.CELL).zip_with(new, value)
            warned[code] = warned[code] | new
            fits = fits | new
        if declared:
            warned.pop(ReadingWarning.MONTH_NAME)
        return (fits, twice, value), warned

    def iso_date(self, *, year: pl.Series, month: pl.Series, day: pl.Series) -> pl.Series:
        """A date from its year, month, and day as text, null where no such day exists."""
        frame = pl.DataFrame({"y": year, "M": month, "d": day})
        written = frame.select(
            pl.format("{}-{}-{}", pl.col("y"), pl.col("M").str.zfill(2), pl.col("d").str.zfill(2)).alias(self.CELL)
        )[self.CELL]
        return written.str.to_date("%Y-%m-%d", strict=False)

    def serial_date(self, serial: str, system: SerialDate) -> datetime | None:
        """A date serial as a moment, or `None` for a serial its system has no date for. Excel's 1900 system counts a
        29 February 1900 that never happened, so serials after it are a day ahead of the calendar."""
        days = float(serial)
        whole = int(days)
        if system == SerialDate.UNIX:
            return self.EPOCH_UNIX + timedelta(seconds=days)
        if system == SerialDate.EXCEL_1904:
            epoch, last = self.EPOCH_1904, self.LAST_SERIAL_1904
        elif whole in (0, self.PHANTOM_LEAP_DAY):
            return None
        else:
            epoch, last = (
                (self.EPOCH_1900 if whole > self.PHANTOM_LEAP_DAY else self.EPOCH_1900_EARLY),
                self.LAST_SERIAL_1900,
            )
        if whole > last:
            return None
        return epoch + timedelta(days=whole, milliseconds=round((days - whole) * self.MILLISECONDS_A_DAY))

    def serials(
        self, *, text: pl.Series, types: pl.Series, fits: pl.Series, value: pl.Series, system: SerialDate
    ) -> tuple[pl.Series, pl.Series, pl.Series, pl.Series]:
        """Read each cell no pattern fitted that is a bare number as a serial, whether text or a stored number. Returns
        what fits, the values, whether a serial held a time, the cell types, a serial then being read, and which cells
        were serials."""
        readable = types.is_in([CellType.STRING.value, CellType.NUMBER.value])
        shape = self.patterns.UNIX_SERIAL if system == SerialDate.UNIX else self.patterns.SERIAL
        serial = (text.str.contains(shape).fill_null(False) & ~fits & readable).alias(self.CELL)
        if not serial.any():
            return fits, value, pl.repeat(False, text.len(), eager=True), types, serial
        moments = {cell: self.serial_date(cell, system) for cell in text.filter(serial).unique().to_list()}
        read = [moments.get(cell) for cell in text.to_list()]
        held_time = [moment is not None and (moment.hour or moment.minute or moment.second) for moment in read]
        written = pl.Series(self.CELL, read, dtype=pl.Datetime("us")).cast(value.dtype)
        tags = pl.repeat(CellType.STRING.value, text.len(), eager=True).zip_with(serial, types)
        held = pl.Series(self.CELL, [bool(held) for held in held_time], dtype=pl.Boolean) & serial
        return fits | serial, written.zip_with(serial, value), held, tags, serial

    def zoned(
        self, *, value: pl.Series, offsets: pl.Series, zone: str | None
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """A datetime in its zone or, with none declared, UTC, from each cell's own offset or its declared clock. Returns
        whether the clocks repeated each time, read as the earlier, and whether a cell has neither offset nor zone."""
        target = zone or self.UTC
        stated = offsets.is_not_null()
        minutes = {cell: self.offset_minutes(cell) for cell in offsets.drop_nulls().unique().to_list()}
        shift = pl.Series(self.CELL, [minutes.get(o, 0) for o in offsets.to_list()], dtype=pl.Int64)
        utc = value.dt.replace_time_zone(self.UTC) - shift.cast(pl.Duration("us")) * self.MICROSECONDS["m"]
        from_offset = utc.dt.convert_time_zone(target).alias(self.CELL)
        if zone is None:
            nothing = pl.repeat(None, value.len(), eager=True, dtype=from_offset.dtype).alias(self.CELL)
            no_zone = ~stated & value.is_not_null()
            return from_offset.zip_with(stated, nothing), pl.repeat(False, value.len(), eager=True), no_zone
        earlier = value.dt.replace_time_zone(target, ambiguous="earliest", non_existent="null").alias(self.CELL)
        later = value.dt.replace_time_zone(target, ambiguous="latest", non_existent="null").alias(self.CELL)
        repeated = (~stated & (earlier != later)).fill_null(False)
        return from_offset.zip_with(stated, earlier), repeated, pl.repeat(False, value.len(), eager=True)

    def offset_minutes(self, offset: str) -> int:
        """A cell's offset from UTC, in minutes: `Z`, `+01`, `+0100`, or `-05:30`."""
        if offset == "Z":
            return 0
        digits = offset[1:].replace(":", "")
        minutes = int(digits[:2]) * 60 + int(digits[2:] or 0)
        return -minutes if offset[0] == "-" else minutes

    def temporal_frame(
        self,
        *,
        cells: pl.Series,
        types: pl.Series,
        mixed: pl.Series,
        fits: pl.Series,
        twice: pl.Series,
        named: pl.Series,
        no_zone: pl.Series | None = None,
        warned: dict[ReadingWarning, pl.Series] | None = None,
    ) -> pl.DataFrame:
        length = cells.len()
        frame = pl.DataFrame(
            {
                "blank": self.is_blank(cells),
                "type": types,
                "form": cells.str.contains(self.patterns.NUMBER_FORM).fill_null(False),
                "mixed": mixed,
                "fits": fits,
                "twice": twice,
                "named": named,
                "no_zone": pl.repeat(False, length, eager=True) if no_zone is None else no_zone,
                **{code.value: flag.fill_null(False) for code, flag in (warned or {}).items()},
            }
        )
        return frame.with_columns(self.temporal_reason())

    def stored_patterns(self, dtype: str) -> list[str]:
        """What a stored date cell's rendering may be, for a type: a datetime at midnight renders as a date, and a period
        is whichever date the cell holds."""
        if dtype in FieldFamilies.PERIODS:
            return [self.STORED_DATETIME_MIDNIGHT]
        canonical = self.CANONICAL[dtype]
        return [*canonical, self.STORED_DATETIME_MIDNIGHT] if dtype == FieldType.DATETIME.value else canonical

    def patterns_read(
        self, *, text: pl.Series, patterns: list[str], rules: RulesModel, dtype: str
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell fits any pattern, whether two read it differently, and its value by the first that fits."""
        fits, twice, value = None, None, None
        for pattern in patterns:
            written = self.pattern_dtype(pattern, dtype)
            tail = dtype == FieldType.DATE.value
            fit, read = self.pattern_value(text=text, pattern=pattern, rules=rules, dtype=written, tail=tail)
            read = read if written == dtype else read.cast(pl.Datetime("us")).alias(self.CELL)
            if fits is None:
                fits, twice, value = fit, pl.repeat(False, text.len(), eager=True).alias(self.CELL), read
                continue
            twice = twice | (fits & fit & (value != read).fill_null(False))
            value = value.zip_with(fits, read)
            fits = fits | fit
        return fits, twice, value

    def pattern_dtype(self, pattern: str, dtype: str) -> str:
        """The type a pattern alone can state: a datetime's stored midnight states only a date."""
        return (
            FieldType.DATE.value
            if pattern == self.STORED_DATETIME_MIDNIGHT and dtype != FieldType.DATE.value
            else dtype
        )

    def temporal_reason(self) -> pl.Expr:
        """Why a date, time, or duration cell is refused, the first of these that holds."""
        refusals = (
            (pl.col("type") == CellType.ERROR.value, RefusalReason.ERROR_CELL),
            (~pl.col("type").is_in([CellType.STRING.value, CellType.DATE.value]), RefusalReason.NOT_IN_FORMAT),
            (pl.col("blank"), None),
            (pl.col("form"), RefusalReason.NUMBER_FORM),
            (pl.col("mixed"), RefusalReason.MIXED_DIGITS),
            (~pl.col("fits"), RefusalReason.NOT_IN_FORMAT),
            (pl.col("twice"), RefusalReason.TWO_READINGS),
            (pl.col("no_zone"), RefusalReason.NO_ZONE),
            (~pl.col("named"), RefusalReason.IMPOSSIBLE_DATE),
        )
        reason = pl.lit(None, dtype=pl.String)
        for condition, refusal in reversed(refusals):
            refused = pl.lit(None, dtype=pl.String) if refusal is None else pl.lit(refusal.value)
            reason = pl.when(condition).then(refused).otherwise(reason)
        return reason.alias("reason")
