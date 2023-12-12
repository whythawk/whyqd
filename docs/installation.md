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

Install with your favourite package manager (minimum of Python 3.9):

```bash
pip install whyqd
```

Then import in Python:

```python
import whyqd as qd
```

## Settings

**whyqd** uses [Ray](https://www.ray.io/) and [Modin](https://modin.readthedocs.io/) as a drop-in replacement for 
[Pandas](https://pandas.pydata.org/) to support processing of large datasets. This is less noticeable if you mostly 
work with <1m rows of data, but the power is there should you need it.

The following can be set in your root `.env` project file:

- `WHYQD_MEMORY`: the memory allocated for processing (e.g. 6Gb, is written in bytes `6000000000`).
- `WHYQD_CPUS`: number of CPUS allocated for parallel processing.
- `WHYQD_SPILLWAY`: Ray will [spill](https://docs.ray.io/en/latest/ray-core/objects/object-spilling.html) to local 
  storage when memory is exceeded. You can specify a temporary folder (default is "/tmp/spill"). This will be automatically
  cleared every time **whyqd** is restarted or reinitialised.
- `WHYQD_DIRECTORY`: a working directory for local storage (default is "").
- `WHYQD_DEFAULT_MIMETYPE`: a default mime type for destination data (default output is 
  "application/vnd.apache.parquet").

The Ray-specific settings are not compulsory. If you don't allocate CPUs or MEMORY, Ray will do its best but if you start
running into problems - especially with larger datasets - have a look at these settings to squeeze out more performance.

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
