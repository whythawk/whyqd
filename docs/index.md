---
title: whyqd - simplicity, transparency, speed
summary: Transform messy data into structured schemas using readable, auditable methods. Perform schema-to-schema crosswalks for interoperability and data reuse.
authors:
  - Gavin Chait
date: 2023-05-03
tags: wrangling, crosswalks, introduction
---
# whyqd: simplicity, transparency, speed

## What is it?

!!! tip ""
    More research, less wrangling

[**whyqd**](https://whyqd.com) (/wɪkɪd/) is a curatorial toolkit intended to produce well-structured and predictable 
data for research analysis.

It provides an intuitive method for creating schema-to-schema crosswalks for restructuring messy data to conform to a 
standardised metadata schema. It supports rapid and continuous transformation of messy data using a simple series of 
steps. Once complete, you can import wrangled data into more complex analytical or database systems.

**whyqd** plays well with your existing Python-based data-analytical tools. It uses [Ray](https://www.ray.io/) and 
[Modin](https://modin.readthedocs.io/) as a drop-in replacement for [Pandas](https://pandas.pydata.org/) to support 
processing of large datasets, and [Pydantic](https://pydantic-docs.helpmanual.io/) for data models. 

Each definition is saved as [JSON Schema-compliant](https://json-schema.org/) file. This permits others to read and 
scrutinise your approach, validate your methodology, or even use your crosswalks to import and transform data in 
production.

Once complete, a transform file can be shared, along with your input data, and anyone can import and validate your 
crosswalk to verify that your output data is the product of these inputs.

## Why use it?

If all you want to do is test whether your source data are even useful, spending days or weeks slogging through data 
restructuring could kill a project. If you already have a workflow and established software which includes Python and 
pandas, having to change your code every time your source data changes is really, really frustrating.

If you want to go from a [Cthulhu dataset](/tutorials/tutorial3) like this:

![UNDP Human Development Index 2007-2008](https://raw.githubusercontent.com/whythawk/whyqd/master/docs/images/undp-hdi-2007-8.jpg)

*UNDP Human Development Index 2007-2008: a beautiful example of messy data.*

To this:

|    | country_name           | indicator_name   | reference   |   year |   values |
|:---|:-----------------------|:-----------------|:------------|:-------|:---------|
|  0 | Hong Kong, China (SAR) | HDI rank         | e           |   2008 |       21 |
|  1 | Singapore              | HDI rank         | nan         |   2008 |       25 |
|  2 | Korea (Republic of)    | HDI rank         | nan         |   2008 |       26 |
|  3 | Cyprus                 | HDI rank         | nan         |   2008 |       28 |
|  4 | Brunei Darussalam      | HDI rank         | nan         |   2008 |       30 |
|  5 | Barbados               | HDI rank         | e,g,f       |   2008 |       31 |

With a readable set of scripts to ensure that your process can be audited and repeated:

```python
schema_scripts = [
    f"UNITE > 'reference' < {REFERENCE_COLUMNS}",
    "RENAME > 'country_name' < ['Country']",
    "PIVOT_LONGER > ['indicator_name', 'values'] < ['HDI rank', 'HDI Category', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']",
    "SEPARATE > ['indicator_name', 'year'] < ';;'::['indicator_name']",
    "DEBLANK",
    "DEDUPE",
]
```

There are two complex and time-consuming parts to preparing data for analysis: social, and technical.

The social part requires multi-stakeholder engagement with source data-publishers, and with
destination database users, to agree structural metadata. Without any agreement on data publication
formats or destination structure, you are left with the tedious frustration of manually wrangling
each independent dataset into a single schema.

**whyqd** allows you to get to work without requiring you to achieve buy-in from anyone or change
your existing code.

## How does it work?

!!! quote "Definition"
    Crosswalks are mappings of the relationships between fields defined in different metadata 
    [schemas](/strategies/schema). Ideally, these are one-to-one, where a field in one has an exact match in
    the other. In practice, it's more complicated than that.

Your workflow is:

1. Define a single destination schema,
2. Derive a source schema from a data source,
3. Review your source data structure,
4. Develop a crosswalk to define the relationship between source and destination,
5. Transform and validate your outputs,
6. Share your output data, transform definitions, and a citation.

It starts like this:

```python
import whyqd as qd
```

[Install](installation) and [get started](quickstart).

!!! abstract "Tutorials"
    There are three worked tutorials to guide you through three typical scenarios:

    - [Aligning multiple data disparate sources to a single schema](/tutorials/tutorial1)
    - [Pivoting wide-format data into archival long-format](/tutorials/tutorial2)
    - [Wrangling Cthulhu data without losing your mind](/tutorials/tutorial3)

## Licence

The [**whyqd** Python distribution](https://github.com/whythawk/whyqd) is licensed under the terms of the 
[BSD 3-Clause license](https://github.com/whythawk/whyqd/blob/master/LICENSE). All documentation is released under 
[Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). **whyqd** tradenames and 
marks are copyright [Whythawk](https://whythawk.com).