---
title: How a cell is read as its type
summary: What a wrangler declares so that each cell reads as its type, what whyqd reads unasked, and the way out for anything else.
date: 2026-11-03
tags: wrangling, types, dates, numbers, reading policy
---
# How a cell is read as its type

**whyqd** reads a cell by what you declare about its field, so the same cell reads the same way on any machine, in any
locale, next year. **Write what you would write in Excel, and whyqd reads what you meant.** It insists only where a cell
truly cannot say what it means.

| A cell | Why it needs a declaration |
|---|---|
| `01/02/2024` | 1 February or 2 January: the cell cannot say |
| `1,234` | One thousand, or 1.234: the cell cannot say |
| `24` as a year | Which century: the cell cannot say |
| `£43.40`, `(5)`, `<5`, `12E4` | What is beside a number may change what it means, so you say which marks a field holds |

A field's declaration is its `policy`:

```python
{"format": "dd/mm/yyyy"}
{"format": "d mmmm yyyy", "rules": {"language": "de"}}
{"format": "dd/mm/yy", "rules": {"yearStart": 1950}}
{"format": {"decimalChar": ",", "groupChar": "."}, "rules": {"currency": ["€"]}}
```

With no `format`, a type reads its plain form: `2024-04-13`, `1234.50`, `true`.

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

## What reads with a warning

These read, and the report says so, because you may want to check them:

| Warning | What happened |
|---|---|
| `year-below-1000` | `01/04/24` under `dd/MM/y` is the year 24, which may be a shortened year. Declare `yy` and `rules.yearStart` if so |
| `time-dropped` | A `date` field's cell also held a time other than midnight. A `datetime` field keeps it |
| `repeated-hour` | The clocks went back, so this time happened twice, and it read as the earlier |

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
