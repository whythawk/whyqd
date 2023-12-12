---
title: Tutorial - Transforming data containing American dates, currencies as strings and misaligned columns
summary: Data curation includes all the processes and techniques needed for ethical and reproducable data creation, management, transformation and presentation for reuse.
authors:
  - Gavin Chait
date: 2023-05-03
tags: wrangling, crosswalks, curation
---
# Tutorial 4: Transforming data containing American dates, currencies as strings and misaligned columns

**whyqd** (/wɪkɪd/) can support you with even the most poorly-formatted and misaligned data through judicious use of schema definitions
and array transforms.

!!! abstract "Learning outcomes"
    - Develop and apply a transformation strategy
    - Apply data types to a source schema to coerce format corrections
    - Collate misaligned data columns into same-length arrays
    - Explode array columns into single-value long-form transformed data

    `SOURCE_DATA` are from [Basildon City Council](https://www.basildon.gov.uk/article/5193/Business-Rates-Published-Data)
    and it is assumed you have familiarity with [Python](https://www.python.org/) and [Pydantic](https://docs.pydantic.dev/).

    ```python
    SOURCE_DATA = "https://github.com/whythawk/whyqd/raw/master/tests/data/raw-e07000066-tutorial-4.xlsx"
    MIMETYPE = "xlsx"
    SCHEMA_DESTINATION = "https://raw.githubusercontent.com/whythawk/whyqd/master/tests/data/test_schema.json"
    ```

## Background

This is a similar use-case as in the [first tutorial](tutorial1.md) based on our [openLocal.uk](https://openlocal.uk) 
project, which is a quarterly-updated commercial location database, aggregating open data on vacancies, rental valuations,
rates and ratepayers, into an integrated time-series database of individual retail, industrial, office and leisure
business units. 

In this tutorial, the source data have been deliberately made worse to illustrate commonly-occuring challenges. These are
problems we regularly experience, just not always in one spreadsheet.

Our source contains the following:

- Dates stored as US-formatted strings (`"MM/DD/YYYY"`)
- Numbers stored as currency strings (`"£45,234.0"`)
- Misaligned fields (there are four tax relief types, but we only have relief amounts for three of these)

We will use **whyqd** (/wɪkɪd/) to transform the data into our schema, and then `pandas` to convert our array values into
a long-form table, using [`explode`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.explode.html):

```python
DataFrame.explode(column, ignore_index=False)
```

## Strategy

!!! tip "Strategy"
    Our source data are in a wide format, meaning that values we would like to be in a single column are provided in
    columns in the source. There's a number of ways we can go about pivoting from wide to long, and here we will 
    assemble an array of values, and then `explode` these fields afterwards. We must be **very** careful to ensure
    that the sequence of each array corresponds so that terms on one array refer to the term at the same position in
    another.

Our source data also include some peculiar data type formatting which can be very stubborn to correct. These include
numbers formatted as currency strings. As example, `"£45,234.0"` where the `£` and `,` are not stylistic but present
in the "number". Most programs will see this as text. Adding `"£45,234.0"` to `"£45,234.0"` will get you 
`"£45,234.0£45,234.0"`, not `"£90,468.0"`.

We also have to deal with American date formats. Americans are the only country in the world to use this format, and
it causes incredible headaches. How should your program interpret something like `1\04\03`? Any of these terms can be
any of a month, day or year. There is no way to algorithmically determine this. You - as the data curator - will need
to make a format decision.

Software can speed up, simplify and make transparent any curation decisions you make, but it cannot replace the insight
which a data owner brings to bear. Don't leave these decisions to the software.

## Define a destination schema

We want our destination data to conform to the following structure:

| la_code  | ba_ref       | occupant_name | postcode | occupation_state | occupation_state_date | prop_ba_rates             | occupation_state_reliefs             |
|:---------|:-------------|:--------------|:-------- |:-----------------|:----------------------|:--------------------------|:-------------------------------------|
|E07000066 | 177500080710 | A company     | PO5 2SE  | True             | 2019-04-01            | [98530, None, 1234, None] | [small_business, None, retail, None] |

We're going to reuse the schema we developed in the [first tutorial](tutorial1.md) but make sure that the `dtype` is an `array`
so we can assemble our destination data:

```python
import whyqd as qd

schema_destination = qd.SchemaDefinition()
schema_destination.set(schema=SCHEMA_DESTINATION)
for field in schema_destination.fields.get_all():
    if field.name in ["occupation_state_reliefs", "prop_ba_rates"]:
        field.dtype = "array"
```

This is our curation foundation for this tutorial and we can save it, ensuring citation and version control.

Set `DIRECTORY`, `FILENAME` and `CREATOR` as per your requirements.

```python
schema_destination.save(directory=DIRECTORY, filename=FILENAME, created_by=CREATOR)
```

We'll reference this definition saved source path as `SCHEMA_DESTINATION` in the rest of this tutorial.

## Source data and source schema definitions

Basildon's data are well-structured but incredibly poor quality:

|    | PlaceRef   | FOIName                            | PropAddress1       | PropAddress2    | PropAddress3   | PropAddress4   | PropAddress5   | PropPostCode   | PropDesc                                  | RateableVal   | MandRlfCd   | MandRlf   | DiscRlfCd   | DiscRlf   | AddRlfCd   | AdditionalRlf   | LiabStart           | RenewableRV   | RnwEn   | SBRFlag   | ChgType   |
|---:|:-----------|:-----------------------------------|:-------------------|:----------------|:---------------|:---------------|:---------------|:---------------|:------------------------------------------|:--------------|:------------|:----------|:------------|:----------|:-----------|:----------------|:--------------------|:--------------|:--------|:----------|:----------|
|  0 | '0664302   | Childs Property Ltd                | 31-33 The Broadway | Wickford        | Essex          | <NA>           | <NA>           | SS11 7AD       | SHOP AND PREMISES                         | £156,000      | <NA>        | £80       | <NA>        | £80       | <NA>       | £80             | 2018-08-01 00:00:00 | £80           | no      | no        | V         |
|  1 | '1065061   | DVS GHL Basildon Limited           | Aviva House        | Southernhay     | Basildon       | Essex          | <NA>           | SS14 1EZ       | OFFICES INCAPABLE OF BENEFICAL OCCUPATION | £157,000      | <NA>        | £88       | <NA>        | £88       | <NA>       | £88             | 2023-06-03 00:00:00 | £88           | no      | no        | V         |
|  2 | '1065061   | Infrared Uk Lion Gp Ltd (in Admin) | Aviva House        | Southernhay     | Basildon       | Essex          | <NA>           | SS14 1EZ       | OFFICES INCAPABLE OF BENEFICAL OCCUPATION | £158,000      | <NA>        | £128      | <NA>        | £128      | <NA>       | £128            | 2022-01-04 00:00:00 | £128          | no      | no        | V         |
|  3 | '1091914   | Kames Capital UK A V P Unit Trust  | Suite 3d           | Southgate House | 88 Town Square | Basildon       | Essex          | SS14 1DT       | UNDERGOING REDEVELOPMENT                  | £158,000      | <NA>        | £128      | <NA>        | £128      | <NA>       | £128            | 1/14/15             | £128          | no      | no        | V         |
|  4 | '0648793   | Orwell (Basildon) Limited          | 62-64 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | UNERGOING REDEVELOPMENT                   | £158,000      | <NA>        | £150      | <NA>        | £150      | <NA>       | £150            | 2/14/20             | £150          | no      | no        | O         |
|  5 | '0648760   | Orwell (Basildon) Limited          | 51-52 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | PREMISES UNDERGOING RECONSTRUCTION        | £158,000      | <NA>        | £150      | <NA>        | £150      | <NA>       | £150            | 2/14/20             | £150          | no      | no        | O         |
|  6 | '0648748   | Orwell (Basildon) Limited          | 38-40 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | PREMISES UNDERGOING RECONSRTUCTION        | £158,000      | <NA>        | £152      | <NA>        | £152      | <NA>       | £152            | 2/14/20             | £152          | no      | no        | O         |
|  7 | '0648679   | Orwell (Basildon) Limited          | 22-24 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | BLDING UNDERGOING WORKS                   | £159,000      | <NA>        | £168      | <NA>        | £168      | <NA>       | £168            | 2/14/20             | £168          | no      | no        | O         |
|  8 | '0720730   | Orwell (Basildon) Limited          | 50-52 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | UNDER RECONSTRUCTION                      | £159,000      | <NA>        | £177      | <NA>        | £177      | <NA>       | £177            | 2/14/20             | £177          | no      | no        | O         |
|  9 | '0648726   | Orwell (Basildon) Limited          | 30-36 Town Square  | Basildon        | Essex          | <NA>           | <NA>           | SS14 1DT       | SHOP & PREMISES                           | £16,000       | <NA>        | £200      | <NA>        | £200      | <NA>       | £200            | 2/14/20             | £200          | no      | no        | O         |

We're going to use **whyqd's** builtin data type coercion to interpret these problems. We do that through setting the `dtype`:

- Column `LiabStart` is of `dtype` `usdate`,
- Columns `MandRlf`, `DiscRlf`, and `AdditionalRlf` are of `dtype` `number`.

```python
CATEGORY_FIELDS = ["MandRlfCd", "DiscRlfCd", "AddRlfCd", "SBRFlag", "ChgType"]
datasource = qd.DataSourceDefinition()
datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)
schema_source = qd.SchemaDefinition()
schema_source.derive_model(data=datasource.get)
for field in schema_source.fields.get_all():
    if field.name in ["LiabStart"]:
        field.dtype = "usdate"
    if field.name in ["MandRlf", "DiscRlf", "AdditionalRlf"]:
        field.dtype = "number"
for cat_field in CATEGORY_FIELDS:
    if cat_field in datasource.get_data().columns:
        schema_source.fields.set_categories(name=cat_field, terms=datasource.get_data())
```

Now we can rely on **whyqd** to correctly interpret the meaning of the values in these columns for the 
crosswalk operations that follow.

## Transformations with crosswalks

Let's define our crosswalk script:

```python
SCRIPTS = [
    "NEW > 'la_code' < ['E07000066']",
    "RENAME > 'ba_ref' < ['PlaceRef']",
    "RENAME > 'occupant_name' < ['FOIName']",
    "RENAME > 'occupation_state_date' < ['LiabStart']",
    "UNITE > 'postcode' < ', '::['PropAddress1','PropAddress2','PropAddress3','PropAddress4','PropAddress5','PropPostCode']",
    "CATEGORISE > 'occupation_state_reliefs'::'exempt' < 'MandRlfCd'::['CASC','EDUC80','MAND80','PCON','POSTO2']",
    "CATEGORISE > 'occupation_state_reliefs'::'discretionary' < 'DiscRlfCd'::['DIS100','DISC10','DISC15','DISC30','DISC40','DISC50','DISCXX','POSTOF']",
    "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'AddRlfCd'::['RETDS3']",
    "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'SBRFlag'::['yes']",
    "CATEGORISE > 'occupation_state'::False < 'ChgType'::['V']",
    "COLLATE > 'prop_ba_rates' < ['MandRlf', 'DiscRlf', 'AdditionalRlf', ~]"
]
```

Most of this should be self-explanatory from the previous tutorials, but here we must pay attention to the order of the scripts. Four
of the `CATEGORISE` scripts refer to the same `occupation_state_reliefs` destination field. However, when you check the corresponding
source data, you'll see that we only have three reliefs value columns. There is no relief amount for the `small_business` category.

If we didn't recognise this, we'd end up with four values in the array for each row the `occupation_state_reliefs` column, and only
three in the `prop_ba_rates` column. We need to use a spacer `modifier`, here defined as `~`.

This allows us to define the [COLLATE](../actions/collate.md) script, with the `~` for the missing column:

```
"COLLATE > 'prop_ba_rates' < ['MandRlf', 'DiscRlf', 'AdditionalRlf', ~]"
```

We can now go ahead and run the crosswalk and transformation:

```python
# Define a Crosswalk
crosswalk = qd.CrosswalkDefinition()
crosswalk.set(schema_source=schema_source, schema_destination=schema_destination)
crosswalk.actions.add_multi(terms=SCRIPTS)
crosswalk.save(directory=DIRECTORY)
# Transform a data source
transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)
transform.process()
transform.save(directory=DIRECTORY, mimetype=DESTINATION_MIMETYPE)
# Validate a data source
DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
valiform = qd.TransformDefinition()
valiform.validate(
    transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
)
```

Our output data look like this:

|     | la_code   | ba_ref   | prop_ba_rates               | occupant_name                           | postcode                                                                                                     | occupation_state   | occupation_state_date   | occupation_state_reliefs             |
|----:|:----------|:---------|:----------------------------|:----------------------------------------|:-------------------------------------------------------------------------------------------------------------|:-------------------|:------------------------|:-------------------------------------|
| 200 | E07000066 | '1157466 | [850.0, 850.0, 850.0, None] |                                         | Unit 2, Great Broomfields, Cranfield Park Road, Wickford, Essex, SS12 9EP                                    | True               | 2021-01-01 00:00:00     | [None, None, None, 'small_business'] |
| 201 | E07000066 | '1033734 | [850.0, 850.0, 850.0, None] |                                         | Unit 3, Tiffaynes Farm, Burnt Mills Road, North Benfleet, Wickford Essex, SS12 9JX                           | False              | 2011-01-04 00:00:00     | [None, None, None, None]             |
| 202 | E07000066 | '1139793 | [850.0, 850.0, 850.0, None] | Alpi Uk Ltd                             | Car Spaces X 6 Alpi, At Alpi House, Miles Gray Road, Basildon, Essex, SS14 3BZ                               | True               | 2018-01-01 00:00:00     | [None, None, None, None]             |
| 203 | E07000066 | '1117835 | [850.0, 850.0, 850.0, None] | A12 Electrical & Technical Limited      | 13 Bowers Court Drive, Bowers Gifford, Basildon, Essex, SS13 2HH                                             | True               | 2010-01-04 00:00:00     | [None, None, None, 'small_business'] |
| 204 | E07000066 | '1002284 | [850.0, 850.0, 850.0, None] | Rotamead Limited                        | Portakabin Building At, Sadlers Hall Farm, London Road, Basildon, Essex, SS13 2HD                            | False              | 2020-03-27 00:00:00     | [None, None, None, None]             |
| 205 | E07000066 | '1099134 | [850.0, 850.0, 850.0, None] | The Electricity Network Company Limited | Independent Distribution Network Operator, Phase 1 Gloucester Park, Broadmayne, Basildon, Essex, SS14 2EB    | True               | 2013-01-04 00:00:00     | [None, None, None, None]             |
| 206 | E07000066 | '1014671 | [850.0, 850.0, 850.0, None] |                                         | Allied Self Drive, Blunts Wall Farm, Blunts Wall Road, Billericay, Essex, CM12 9SA                           | False              | 2013-01-11 00:00:00     | [None, None, None, None]             |
| 207 | E07000066 | '1126950 | [850.0, 850.0, 850.0, None] | Basildon & Thurrock Uni Hosp Nhs Trust  | Phlebotomy Office, Billericay St Andrews Centre, Stock Road, Billericay, Essex, CM12 0BH                     | True               | 2015-01-04 00:00:00     | [None, None, None, None]             |
| 208 | E07000066 | '1126938 | [850.0, 850.0, 850.0, None] | Basildon & Thurrock Uni Hosp Nhs Trust  | Phlebotomy Cubicle 1, Billericay St Andrews Centre, Stock Road, Billericay, Essex, CM12 0BH                  | True               | 2015-01-04 00:00:00     | [None, None, None, None]             |
| 209 | E07000066 | '1114461 | [850.0, 850.0, 850.0, None] | Veolia Pitsea Marshes Maintenance Trust | Unit D White Cottages & Workshop, Wat Tyler Country Park, Pitsea Hall Lane, Pitsea, Basildon Essex, SS16 4UH | True               | 2016-09-26 00:00:00     | ['exempt', None, None, None]         |

## Integration of transformed data into other applications

The objective of a **whyqd** transform isn't just archival data, but as an input in other research or applications. These arrays are
very efficient for storage, but aren't particularly useful for anything else. We can quickly recover the full long-form data structure
using [`explode`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.explode.html) applied to the array fields:

```python
df = transform.data.copy()
df = df.explode(["occupation_state_reliefs", "prop_ba_rates"])
df.drop_duplicates(inplace=True)
```

Which gives us this:

|      | la_code   | ba_ref   |   prop_ba_rates | occupant_name                              | postcode                                                                                                      | occupation_state   | occupation_state_date   | occupation_state_reliefs   |
|-----:|:----------|:---------|----------------:|:-------------------------------------------|:--------------------------------------------------------------------------------------------------------------|:-------------------|:------------------------|:---------------------------|
| 1382 | E07000066 | '1127679 |            5800 | Gould Barbers East Anglia Limited          | Gould Barbers, At Tesco, Mayflower Retail Park, Gardiners Lane South, Basildon Essex, SS14 3HZ                | True               | 2018-10-01 00:00:00     | retail                     |
| 1383 | E07000066 | '0638697 |            5800 | Infrared Uk Lion Gp Ltd (in Admin)         | Public Conveniences, Eastgate, Basildon, Essex, SS14 1AE                                                      | True               | 2022-01-04 00:00:00     | exempt                     |
| 1386 | E07000066 | '1058511 |            5800 | <NA>                                       | Workshop @, Basildon Motoring Centre, Long Riding, Basildon, Essex, SS14 1QY                                  | True               | 2010-02-04 00:00:00     | retail                     |
| 1388 | E07000066 | '0654079 |            5800 | Noak Bridge Community Association          | Noak Bridge Village Hall, Coppice Lane, Basildon, Laindon, Essex, SS15 4JS                                    | True               | 1995-01-04 00:00:00     | exempt                     |
| 1388 | E07000066 | '0654079 |            5800 | Noak Bridge Community Association          | Noak Bridge Village Hall, Coppice Lane, Basildon, Laindon, Essex, SS15 4JS                                    | True               | 1995-01-04 00:00:00     | retail                     |
| 1434 | E07000066 | '0643641 |            6000 | South Green and District War Memorial Fund | South Green Memorial Hall, Southend Road, Billericay, Essex, CM11 2PR                                         | True               | 1995-01-04 00:00:00     | exempt                     |
| 1434 | E07000066 | '0643641 |            6000 | South Green and District War Memorial Fund | South Green Memorial Hall, Southend Road, Billericay, Essex, CM11 2PR                                         | True               | 1995-01-04 00:00:00     | retail                     |
| 1435 | E07000066 | '0433089 |            6000 |                                            | 86 Pound Lane, Basildon, Pitsea, Essex, SS13 2HW                                                              | True               | 2004-05-11 00:00:00     | retail                     |
| 1448 | E07000066 | '1162681 |            6100 | New Life Wood                              | West Of Unit A The Old Laboratory, Wat Tyler Country Park, Pitsea Hall Lane, Pitsea, Basildon Essex, SS16 4UH | True               | 2021-05-31 00:00:00     | exempt                     |
| 1452 | E07000066 | '1127975 |            6100 | Royal Voluntary Service                    | RVS Shop At Antenatal Unit, Basildon Hospital, Nethermayne, Basildon, Essex, SS16 5NL                         | True               | 2015-01-04 00:00:00     | exempt                     |

