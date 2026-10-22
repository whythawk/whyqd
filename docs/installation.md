---
title: Installation and environment settings
summary: Transform messy data into structured schemas using readable, auditable methods. Perform schema-to-schema crosswalks for interoperability and data reuse.
authors:
  - Gavin Chait
date: 2023-12-12
tags: wrangling, crosswalks, installation
---
# Installation and environment settings

**whyqd** (/wɪkɪd/) can be integrated into an existing data importer, or you could use it as part of your
data analysis and exploration in Jupyter Notebooks.

## Install

Install with your favourite package manager. You'll need Python 3.12.

```bash
pip install whyqd
```

Then import in Python:

```python
import whyqd as qd
```

## Settings

The following can be set in your root `.env` project file:

- `WHYQD_DIRECTORY`: a working directory for local storage (default is "").
- `WHYQD_DEFAULT_MIMETYPE`: a default mime type for destination data (default output is 
  "application/vnd.apache.parquet").

**whyqd** supports any of the following file mime types:

- `CSV`: "text/csv"
- `XLS`: "application/vnd.ms-excel"
- `XLSX`: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
- `PARQUET` (or `PRQ`): "application/vnd.apache.parquet"
- `FEATHER` (or `FTR`): "application/vnd.apache.feather"

Declare it like so:

```python
MIMETYPE = "xlsx" # upper- or lower-case is fine
```

Neither of [Parquet](https://parquet.apache.org/docs/overview/) or 
[Feather](https://arrow.apache.org/docs/python/feather.html) yet have official mimetypes, so this is what we're using 
for now.
