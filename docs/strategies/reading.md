---
title: How a cell is read as its type
summary: What whyqd reads once you give a field a type, what it warns of, what only a declaration settles, and the way out for anything else.
date: 2026-11-20
tags: wrangling, types, dates, numbers, reading policy, warnings
---
# How a cell is read as its type

**whyqd** reads a cell by the type you give its field and what you declare about it, so the same cell reads the same
way on any machine, in any locale, next year. **Nothing is typed until you say so**: a field with no type stays text.
**Once you give it a type, whyqd works to make each cell fit, and says what it did.** Write what you would write in
Excel, and whyqd reads what you meant.

| A cell, in a `number` or `date` field | What happens |
|---|---|
| `£43.40`, `(5)`, `5%`, `1,234.50`, `1e3` | Reads, as 43.40, -5, 0.05, 1234.5, and 1000, with a warning saying what was read |
| `13/04/2024`, `1 April 2024`, `45295` | Reads, as 2024-04-13, 2024-04-01, and 2024-01-04, with a warning |
| `01/02/2024` | Halts: 1 February or 2 January, and the cell cannot say |
| `1,234` | Halts: one thousand, or 1.234, and the cell cannot say |
| `24` as a year | Halts: which century, and the cell cannot say |
| `<5`, `10 - 20`, `TBC` | Halts: no reading would be honest |

**A guess and a reading are different things.** whyqd never guesses what type a column is. Once you have said it is a
number, a cell such as `£5` has one sensible reading, and whyqd reads it rather than refusing you. **A column never
votes**: `13/04/2024` settles only its own cell, never its neighbour `01/02/2024`.

A field's declaration is its `policy`. It settles what a cell cannot, and confirms a reading, which then no longer
warns:

```python
{"format": "dd/mm/yyyy"}
{"format": "d mmmm yyyy", "rules": {"language": "de"}}
{"format": "dd/mm/yy", "rules": {"yearStart": 1950}}
{"format": {"decimalChar": ",", "groupChar": "."}, "rules": {"currency": ["€"]}}
```

With no `format`, a type reads its plain form silently: `2024-04-13`, `1234.50`, `true`.

**Declaring also tightens.** Once a field declares currencies, negative forms, or the decimal and group marks, a cell
written another way refuses, since you have said what the file holds. Under `{"rules": {"currency": ["€"]}}`, `£5`
refuses.

## Numbers

**What reads with a warning, where the field declares nothing of the kind:**

- A currency symbol, `£`, `$`, `€`, or any other of Unicode's currency symbols, and `¬£`, the garbled `£` of a file
  read in the wrong encoding. A currency in letters, such as `CHF` or `kr`, must be declared in `rules.currency`.
- A negative written `(5)` or `5-`. Any other form, such as `5 CR`, must be declared in `rules.negative`.
- A percent, `5%`, as 0.05. An exponent, `1e3`, as 1000; set `rules.exponent` to `false` if `12E4` is a reference.
- The marks `.` and `,`, wherever only one reading fits: with both in a cell the last is the decimal (`1,234.50`,
  `1.234,50`); a repeated mark groups (`1,234,567`, and Indian `12,34,567`); and a lone mark is the decimal unless three
  digits follow one to three digits, as in `1,234`, which in some places means one thousand and in others 1.234. That
  one must be declared, in `format`. So must a space or `’` grouping digits, since a space can also part two numbers.
- In an `integer` field, a fraction, rounded half away from zero as Excel's `ROUND` does: `5.5` is 6, `-5.5` is -6.
- A number with more digits than a `Float64` holds, such as `12345678901234567890`: the column reads as exact decimals,
  so none are lost. Declare `"base": "decimal"` where exact values matter, such as money.

**A sign is never dropped**, and `<5`, `~5`, or `±5` never reads as 5. `NaN` and `INF` read only once
`rules.nonFinite` is set.

**A field holding more than one currency warns, with each one's count.** Reading a number loses which currency it was
in, so nobody should sum them by accident.

## The way out

**Nothing has to be read as a type.** A field of type `string` keeps every cell exactly as written and refuses nothing, so
a column that cannot be described, such as `c. 1850` or `1st April 2024`, always has somewhere to go. Split it with a
crosswalk action, or hand it on as text.

For a really specialist type, a package will be able to provide its own as an extension, declared by the definition that
uses it. Registering and declaring one works today; running one is still being built.

## Dates and times

**Write a pattern as Excel does, as Python's `strptime` does, or as
[Unicode's UAX 35](https://www.unicode.org/reports/tr35/tr35-dates.html#Date_Field_Symbol_Table) does.** whyqd saves it as
UAX 35 writes it, which is what [CSV on the Web](https://www.w3.org/TR/tabular-metadata/#derived-datatypes) reads, so you
can always see how it was understood:

| You write | Saved as |
|---|---|
| `dd/mm/yyyy`, `DD/MM/YYYY`, `%d/%m/%Y` | `dd/MM/yyyy` |
| `dd/mm/yyyy hh:mm` | `dd/MM/yyyy HH:mm` |
| `M/d/yyyy h:mm AM/PM` | `M/d/yyyy h:mm a` |
| `yyyy-MM-ddTHH:mm:ssZ` | `yyyy-MM-dd'T'HH:mm:ss` |

`m` is minutes beside an hour or a second and otherwise a month, which is Excel's own rule.

**With no pattern declared, a date with one reading reads, with a warning**, in three shapes:

- Day and month as numbers in either order, a four-digit year last, one separator used twice: `13/04/2024`, whose 13
  can only be a day, or `31.12.2024`. `01/02/2024` halts, being either; `04/04/2024` reads, being the same day either way.
- Digits run together as `yyyyMMdd`: `20240413`.
- A day, a month's name, and a four-digit year, either of the first two first: `1 April 2024`, `Dec 31, 2024`. A name
  reads only where it means one month in every language whyqd holds. `listopad` is October in Croatian and November in
  Czech, so it halts until you declare `rules.language`; so does English `Jan`, which is June in Southern Sotho.

A two-digit year, a year first (`2024/04/13`), or a further word halts. **A declared pattern settles a field**, so a cell
it cannot read refuses and is never read another way.

**What reads without being declared**, because the cell is clear:

- A number's width says nothing of its meaning, so `dd` reads `1` and `13`, unless digits run together, as in `yyyyMMdd`.
- A decimal digit of any script reads as its value: `٣` is 3.
- `2024-04-13 00:00:00` reads as a date, and `9:30 pm` as a time, whichever way it is written.
- A datetime's own offset reads wherever a cell has one: `12:45:00+01:00` is 11:45 UTC. Declare `rules.zone` for a clock
  with none.

**Names need only their language.** `{"language": "de"}` reads every month and weekday name Unicode's
[CLDR](https://cldr.unicode.org/) holds for it, in any case and with or without a closing dot, so `Sep`, `Sept`, `SEPT.`,
and `September` are all September. whyqd keeps its own fixed copy, so no library or machine can change a read. Add other
spellings in `rules.monthNames`. `AM` and `PM` are always read, and a weekday is read past, not checked against its date.

**A period reads as the date it ends on**, as a `month`, `quarter`, or `year` field: `2024-04` is 2024-04-30, `2024` is
2024-12-31, and `2024Q2` under `yyyy'Q'Q` is 2024-06-30.

**A bare number in a date field reads as a date serial, with a warning.** Excel stores a date as a count of days, and
sometimes that count is all that reaches you: `45295` in a date column, as a number or as text. Text is read by
`excel-1900`, which nearly every workbook uses, and the warning names it, since `excel-1904`, used by some older
workbooks from a Mac, differs by four years. Declare the system to confirm it, beside any patterns:

```python
{"format": "dd/mm/yyyy", "rules": {"serial": "excel-1900"}}
```

`45295` is then 2024-01-04, and `45295.5` is noon that day in a `datetime` field. `unix` reads seconds since
1970-01-01 UTC. A `year` field's bare number is a year, and a field whose pattern is digits alone, such as `yyyyMMdd`,
has already said what a bare number is, so neither reads a serial unless you declare one.

## What reads with a warning

These read, and the report says so, with how many cells and the first row, because you may want to check them. Declare
what was read, and the warning goes:

| Warning | What happened | Confirm it with |
|---|---|---|
| `currency-read` | A currency symbol was read past | `rules.currency` |
| `sign-read` | `(5)` or `5-` read as negative | `rules.negative` |
| `percent-read` | `5%` read as 0.05 | `rules.percent` |
| `marks-read` | The cell's own marks settled which is the decimal | `format` |
| `exponent-read` | `1e3` read as 1000 | `rules.exponent` |
| `exact-decimal` | More digits than a `Float64` holds, so the column read as exact decimals | `"base": "decimal"` |
| `integer-rounded` | A fraction rounded half away from zero | A `number` field keeps it |
| `serial-read` | A bare number read as a date serial, text by `excel-1900` | `rules.serial` |
| `month-name-read` | A month's name read with no language declared | `rules.language` |
| `date-order-read` | The cell's own digits settled the day and month, as in `13/04/2024` | `format` |
| `year-below-1000` | `01/04/24` under `dd/MM/y` is the year 24, which may be a shortened year | `yy` and `rules.yearStart` |
| `time-dropped` | A `date` field's cell also held a time other than midnight | A `datetime` field keeps it |
| `repeated-hour` | The clocks went back, so this time happened twice, and it read as the earlier | |
| `boolean-as-number` | A boolean mapped to a number, or stored in a number field, read `true` as 1 and `false` as 0 | |
| `number-as-boolean` | A number mapped to a boolean, or stored in a boolean field, read 1 as `true` and 0 as `false`; any other number halts | |

A cell may carry several: `£1,234.50` warns of its currency and its marks.

**A warning never stops a transform; a halt always does.** A transform either builds a table that conforms to its
destination schema, or raises `ConformanceError` with a report of every cell and constraint that stopped it.
`process(strict=True)` treats every warning as a fault too, for a run that must have nothing to check.

## Presence as a boolean

A field of any type may stand for presence: a relief is present where its start date is. Derive its categories as
booleans with `set_categories(name=..., as_bool=True)`, and `CATEGORISE` assigns `True` to each cell holding a value of
its type. The cell is read as its type first, so `TBC` in a date field halts. **A blank is never present, and a zero is
absent**, unless `zero_as_true=True` counts it, on a number or integer field.

## What Excel did before whyqd saw the file

Excel turns text into dates on opening, using the opener's locale. A day-first `04/01/1997`, opened under a month-first
locale, is stored as 1 April; `13/04/2024` cannot be a month-first date, so it stays as text. The mirror case does the
reverse.

**A stored date is a value, so whyqd reads it as stored, and a swapped cell reads wrongly until you say otherwise.** One
cell cannot show that it was swapped. A column of date cells whose days never pass 12, beside text cells whose days
always do, is the sign to look for. Declare the text's pattern, and a pattern for the stored cell:

```python
{"format": "dd/mm/yyyy", "rules": {"cellFormats": {"d": "yyyy-dd-MM"}}}
```

## If this gets in your way

**Please [open an issue](https://github.com/whythawk/whyqd/issues) with the form you met.** whyqd departs from its
standards in a few places, listed below, and these choices are being watched: that is how we will know one is wrong.

| Choice | Why |
|---|---|
| A pattern may be typed in several spellings, and is saved in one | So you need not learn UAX 35, where `mm` means minutes |
| `yy` needs `rules.yearStart`, the first of its 100 years, a fixed year | `1950` reads `49` as 2049 and `50` as 1950, and reads the same next year, which a rolling window would not |
| Names come from whyqd's own copy of CLDR | A locale library's names change between versions |
| A duration's text uses the same letters, as quantities: `H:mm` reads `100:30`, and `m' min'` reads `25 min` | UAX 35 has no duration pattern. Years and months have no fixed length, so neither is read |
| A clock time the clocks skipped refuses | It never happened |
| A cell with one sensible reading reads, with a warning, rather than refusing | You said what type the field is; refusing `£5` in a number field would only make you work around it |
| An undeclared month name reads only where it means one month in every language | English `Jan` halts, being June in Southern Sotho: declare `rules.language` |
| A lone mark with three digits after one to three, as `1,234`, halts until declared | It means one thousand in some places and 1.234 in others |
| A bare number in a date field reads by `excel-1900` | Nearly every workbook uses it; the warning names it, since `excel-1904` is four years apart |
| An integer field rounds half away from zero | Excel's `ROUND` does; half to even would read `2.5` as 2 |
| One cell too long for a `Float64` makes its column exact decimals | A column holds one type, and losing the digits would be silent |
