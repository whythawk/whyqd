---
title: Tutorial - Aligning multiple sources of local government data from a many-headed Excel spreadsheet to a single schema
summary: Data curation includes all the processes and techniques needed for ethical and reproducable data creation, management, transformation and presentation for reuse.
authors:
  - Gavin Chait
date: 2023-05-03
tags: wrangling, crosswalks, curation
---
# Tutorial 1: Aligning multiple sources of local government data from a many-headed Excel spreadsheet to a single schema

**whyqd** (/wɪkɪd/) was developed to solve a daily, grinding need. This tutorial is based on a real-world problem.

!!! abstract "Learning outcomes"
    - Develop and apply a transformation strategy
    - Design and create a standardised destination schema
    - Extract source data and derived individual source schemas
    - Perform crosswalks and validations

    `SOURCE_DATA` are from [Portsmouth City Council](https://www.portsmouth.gov.uk/ext/business/running-a-business/business-rates-foi-requests)
    and it is assumed you have familiarity with [Python](https://www.python.org/) and [Pydantic](https://docs.pydantic.dev/).

    ```python
    SOURCE_DATA = "https://github.com/whythawk/whyqd/blob/d95b9a8dc917ed119f0b64cb2a3f699e4fee7a8d/tests/data/raw_multi_E06000044_014.xlsx"
    MIMETYPE = "xlsx"
    ```

## Background

Our [openLocal.uk](https://openlocal.uk) project is a quarterly-updated commercial location database, aggregating open 
data on vacancies, rental valuations, rates and ratepayers, into an integrated time-series database of individual 
retail, industrial, office and leisure business units. 

Every three months, we import about 300 very messy spreadsheets from local authorities across the UK. These need to be 
restructured to conform to a single schema, including redefining whatever weird terms they use to describe categorical 
data, and only then can we begin the automated process of cleaning and validation.

Our work is mainly used by researchers and the UK government but, during COVID in 2020-21, these data took on political
and economic heft when they were part of the research base informing impact assessment for the various lockdowns and 
the economic recovery afterwards.

[Levelling Up](https://commonslibrary.parliament.uk/which-areas-have-benefited-from-the-levelling-up-fund/) awarded
almost £4 billion to projects across the UK. But for some to get, others had their requests refused.

The rejected began to aggressively question the entire evidence supporting the allocation, and openLocal was targeted. 
The strategy and approach presented here made it straightforward for us to demonstrate how we ensure data probity. We 
[wrote up our methods](https://github.com/whythawk/barnsley-location-data-review).

Curation makes your workflow more efficient, but it can also keep you out of legal peril.

## Strategy

!!! tip "Strategy"
    Our objective is a sequential event-based data series, capturing everything that happened for every commercial 
    address in a particular source authority. Since multiple things can happen on a single date which may be presented
    in an ambiguous way from the source, we may end up "losing" some data but as long as we can recover information 
    from the sequence, we're good.

Our source data can be in any tabular format (XLS, XLSX and CSV). There are no common rates data management systems, no 
agreed schema or terminology, and high staff turnover means change in data structure from the same sources between 
releases.

Given this diversity, we have a single **acceptance criterion** to include a source in an update process: it **must**
include a field for the data we use as a **foreign key** for cross-data merging. It doesn't matter if it's in poor
quality, but it must be there.

We also need a single **destination schema** which is common across the project.

If we're really lucky, our data source don't change their definitions or structure from release-to-release and we can 
reuse our crosswalks. In our experience that is like searching for unicorns.

## Define a destination schema

We want our destination data to conform to the following structure:

| la_code  | ba_ref       | occupant_name | postcode | occupation_state | occupation_state_date | prop_ba_rates | occupation_state_reliefs |
|:---------|:-------------|:--------------|:-------- |:-----------------|:----------------------|:--------------|:-------------------------|
|E06000044 | 177500080710 | A company     | PO5 2SE  | True             | 2019-04-01            | 98530         | [small_business, retail] |

Review the [schema documentation](../strategies/schema.md) for more details, but these are the `type` of data we need here:

- `string`: any text-based string.
- `number`: any number-based value, including integers and floats.
- `boolean`: a boolean [`True`, `False`] value. Can set category constraints to fix term used.
- `array`: any valid array-based data (used for a list of categorical terms).
- `date`: any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`.

In addition, these data can be `constrained`:

- `required`: boolean, indicates whether this field is compulsory (but blank values in the input column are permitted 
  and will be set to the missing default),
- `category`: the set of unique category terms permitted in this field.

Let's start:

```python
import whyqd as qd

schema_destination = qd.SchemaDefinition()
# Using Pydantic model validation
schema: qd.models.SchemaModel = {
  "name": "rates_data_schema",
  "title": "UK Ratepayer data schema",
  "description": "Structural metadata target for imported messy data from the 348 local authorities in England & Wales."
}
schema_destination.set(schema=schema)
```

We'll build a single fields dictionary and then iterate over the list to add each field:

```python
fields = [
  {
    "name": "la_code",
    "title": "Local authority code",
    "type": "string",
    "description": "Standard code for local authority."
  },
  {
    "name": "ba_ref",
    "title": "Billing reference",
    "type": "string",
    "description": "Unique code for a specific hereditament. May be multiple rows for history."
  },
  {
    "name": "prop_ba_rates",
    "title": "Property billing rates",
    "type": "number",
    "description": "Actual rates paid by a specific ratepayer."
  },
  {
    "name": "occupant_name",
    "title": "Occupier name",
    "type": "string",
    "description": "Name of the ratepayer."
  },
  {
    "name": "postcode",
    "title": "Postcode",
    "type": "string",
    "description": "Full address or postcode of ratepayer."
  },
  {
    "name": "occupation_state",
    "title": "Occupation state",
    "type": "boolean",
    "description": "Occupation status, void or occupied."
  },
  {
    "name": "occupation_state_date",
    "title": "Date of occupation state",
    "type": "date",
    "description": "Date of the start of status in occupation_state."
  },
  {
    "name": "occupation_state_reliefs",
    "title": "Occupation state reliefs",
    "type": "array",
    "description": "Array of the categories of reliefs / exemptions applied."
  }
]
schema_destination.fields.add_multi(terms=fields)
```

From here on we can access any `field` by calling it by `name` and then updating it as required:

```python
schema_destination.fields.get(name="occupation_state_reliefs")
```

Let's add a list of `category` terms as a constraint for `occupation_state_reliefs`. These are derived from the official 
business [rates reliefs](https://www.gov.uk/apply-for-business-rate-relief):

```python
categories = [
  "small_business", "rural", "charity", "enterprise_zone", "vacancy", 
  "hardship", "retail", "discretionary", "exempt", "transitional", "other"
]
constraints = {
    "categories": [{
      "name": category for category in categories
    }]
  }
schema_destination.fields.set_constraints(name="occupation_state_reliefs", constraints=constraints)
```

Use `.dict(by_alias=True, exclude_defaults=True, exclude_none=True)` to extract a dictionary format from the underlying
[Pydantic](https://pydantic-docs.helpmanual.io/) model.

```python
schema_destination.fields.get(name="occupation_state_reliefs"
                              ).dict(
                                by_alias=True, 
                                exclude_defaults=True, 
                                exclude_none=True)

{
  'uuid': UUID('cf4d066e-22a8-4b76-8956-f6120eec4c52'),
  'name': 'occupation_state_reliefs',
  'title': 'Occupation state reliefs',
  'description': 'Array of the categories of reliefs / exemptions applied.',
  'type': 'array',
  'constraints': {
    'enum': [
      {
        'uuid': UUID('daa206a9-ac8c-41a9-a504-06410780ee50'),
        'name': 'small_business'
      },
      {
        'uuid': UUID('5964e9fc-dd50-4856-acdc-2326ea48ef1d'), 
        'name': 'rural'
      },
      {
        'uuid': UUID('498654f9-8825-4f3d-a573-0c110726fba4'), 
        'name': 'charity'
      },
      {
        'uuid': UUID('f94353ce-a489-4fb1-ad78-5435b3dd54a4'),
        'name': 'enterprise_zone'
      },
      {
        'uuid': UUID('41285fc0-2321-4542-b7f1-e8e535588559'), 
        'name': 'vacancy'
      },
      {
        'uuid': UUID('28068ff2-15ff-409a-9a8f-f97c39407812'), 
        'name': 'hardship'
      },
      {
        'uuid': UUID('b8041d21-f8ca-47b9-b3fe-7b9077388459'), 
        'name': 'retail'
      },
      {
        'uuid': UUID('83bda0d4-3d94-4738-a580-cfe0881c8e4d'),
        'name': 'discretionary'
      },
      {
        'uuid': UUID('ff2cbc0c-839b-430c-bdca-ac4238634f05'), 
        'name': 'exempt'
      },
      {
        'uuid': UUID('f4300571-c04b-4cbf-b835-16c5ae3343b0'),
        'name': 'transitional'
      },
      {
        'uuid': UUID('8a3af6f4-f48c-4614-83f2-ba472b2129e9'), 
        'name': 'other'
      }
    ]
  }
}
```

This is our curation foundation and we can save it, ensuring citation and version control.

```python
schema_destination.save(directory=DIRECTORY, filename=FILENAME, created_by=CREATOR)
```

We'll reference this definition saved source path as `SCHEMA_DESTINATION` in the rest of the tutorial.

## Source data and source schema definitions

Portsmouth data are reasonably well-structured:

![Semi-ideal primary source data](../images/ideal-primary-data.png)

However, once you import and derive its data model you'll discover a slight hiccough:

```python
datasource = qd.DataSourceDefinition()
datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)

if isinstance(datasource.get, list):
  print(len(datasource.get))

3
```

If you look at the spreadsheet at the same time, you'll see it's an Excel file with three tabs. **whyqd** has
automatically imported all three, and derived the data model for each. Let's review:

- Each data model has a different set of columns, meaning there is no common source schema or crosswalk,
- There **is** a foreign key for each, so they meet our minimum acceptance criteria.

Turns out you don't have *one* transformation, you need to do three.

Now *technically*, because there are so many common fields, we could create a single source schema and use it for all
three source tabs, but let's use a verbose approach for this tutorial and create three separate source schemas.

We also recognise that two columns are used to define our categorical data. We need to extract the terms used in these
columns so we can assign them appropriately later:

```python
CATEGORY_FIELDS = ["Current Relief Type", "Current Property Exemption Code"]
SCHEMA_SOURCE = {}
DATA_SOURCE = {}

for ds in datasource.get:
    DATA_SOURCE[ds.sheet_name] = ds
    schema_source = qd.SchemaDefinition(source={
          "name": f"portsmouth-{ds.sheet_name.lower()}"
    })
    schema_source.derive_model(data=ds)
    field_names = [c.name for c in ds.columns]
    if not set(CATEGORY_FIELDS).isdisjoint(field_names):
        # we don't want to load the data if don't need
        # whyqd will only load the needed sheet as defined in the data model
        df = datasource.reader.get(source=ds)
        for category_field in CATEGORY_FIELDS:
            if category_field in df.columns:
                schema_source.fields.set_categories(name=category_field, terms=df)
    SCHEMA_SOURCE[ds.sheet_name] = schema_source
```

Leaving us with a list of source schema, along with their appropriate categories:

```python
SCHEMA_SOURCE["Report1"].get.dict(by_alias=True, exclude_defaults=True, exclude_none=True)

{'uuid': UUID('a25091ef-2bad-4207-8e04-dc50760de5f9'),
 'name': 'portsmouth-report1',
 'fields': [{'uuid': UUID('b5a4592c-46a3-41fb-aa22-9f48400e09ae'),
   'name': 'Property Reference Number',
   'title': 'Property Reference Number',
   'type': 'string'},
  {'uuid': UUID('3c31d709-4c37-4830-9781-391bf3a990cb'),
   'name': 'Primary Liable party name',
   'title': 'Primary Liable party name',
   'type': 'string'},
  {'uuid': UUID('86145ff6-973f-4f6e-85ce-f5c73d3da9ca'),
   'name': 'Full Property Address',
   'title': 'Full Property Address',
   'type': 'string'},
  {'uuid': UUID('f6690650-908b-4b1c-90e1-1f81470bb7e4'),
   'name': 'Current Relief Type',
   'title': 'Current Relief Type',
   'type': 'string',
   'constraints': {'enum': [{'uuid': UUID('619941f4-719c-43d9-be70-30343366e51d'),
      'name': 'Retail Discount'},
     {'uuid': UUID('dcaccfdc-cdec-4e60-a3ab-bcade51260cf'),
      'name': 'Small Business Relief England'},
     {'uuid': UUID('436bc5c4-c627-4b99-b82e-cde5c2f8a329'),
      'name': 'Mandatory'},
     {'uuid': UUID('0e228796-815b-404e-99e8-c19572e6a414'),
      'name': 'Empty Property Rate Non-Industrial'},
     {'uuid': UUID('76f56e35-9c70-4d5c-85ce-c8fe61479944'),
      'name': 'Empty Property Rate Industrial'},
     {'uuid': UUID('3d1b5668-f14e-42a8-80f3-ca60b0cccbc3'),
      'name': 'Supporting Small Business Relief'},
     {'uuid': UUID('1deb0ab9-b630-4b61-8fb6-8a78fea8dfac'),
      'name': 'Sports Club (Registered CASC)'},
     {'uuid': UUID('a8ad1f3f-fea6-4e2f-b5cf-000c0b53e900'),
      'name': 'Sbre Extension For 12 Months'},
     {'uuid': UUID('01c067be-3ce9-4059-a8dd-c0bcfe664fc3'),
      'name': 'Empty Property Rate Charitable'}]}},
  {'uuid': UUID('ab9a4381-657c-419d-995f-28d2ec1eda87'),
   'name': 'Account Start date',
   'title': 'Account Start date',
   'type': 'string'},
  {'uuid': UUID('646743e4-b70b-4f9d-b891-c856b7755296'),
   'name': 'Current Relief Award Start Date',
   'title': 'Current Relief Award Start Date',
   'type': 'string'},
  {'uuid': UUID('4f814e7a-8c29-4736-a7de-59a54b138236'),
   'name': 'Current Rateable Value',
   'title': 'Current Rateable Value',
   'type': 'string'}],
 'attributes': {'rowCount': 3421}}
```

## Defining crosswalks

Fortunately, this isn't a particularly difficult crosswalk, with only the categorisations requiring any complexity, and
we need to create one column for the local authority itself so that we can track each dataset when we do the eventual
merge into the database.

Portsmouth has the [census code `E06000044`](https://www.ons.gov.uk/geography/local-authority/E06000044) which we use as
an additional foreign key. 

Let's define our three crosswalks and then review:

```python
SCHEMA_SCRIPTS = {
    "Report1": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property Reference Number']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "CATEGORISE > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
        "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
        "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
        "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
        "CATEGORISE > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
        "SELECT_NEWEST > 'occupation_state_date' < ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date' + 'Account Start date']",
    ],
    "Report2": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property Reference Number']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "CATEGORISE > 'occupation_state'::False < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
        "CATEGORISE > 'occupation_state_reliefs'::'enterprise_zone' < 'Current Property Exemption Code'::['INDUSTRIAL']",
        "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
        "CATEGORISE > 'occupation_state_reliefs'::'exempt' < 'Current Property Exemption Code'::['C', 'LOW RV', 'LAND']",
        "RENAME > 'occupation_state_date' < ['Current Prop Exemption Start Date']",
    ],
    "Report3": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property ref no']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "RENAME > 'occupation_state_date' < ['Account Start date']",
    ],
}
```

Remember the basic structure of an `script`: `ACTION > DESTINATION < [SOURCE]`.

We're using only four types of action. `NEW` and `RENAME` should be self-explanatory, but let's look at two the others.

The `Report1` tab has two date fields. One for the date a specific relief was awarded, and the other for when the 
ratepayer became responsible for the account. It may happen that a ratepayer starts on the same day they receive a
relief. They may also be discrete events, meaning that there'd be an entry when they become the account-holder and 
another when they are awarded the relief. We get both dates on each row. How to choose which is relevant?

```python
"""
SELECT_NEWEST > 'occupation_state_date' 
          < 
          ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 
          'Account Start date' + 'Account Start date']
"""
```

`SELECT_NEWEST` means take the latest field from the list of fields. We create a list of source choices with a `MODIFIER`.

The format is `'target_field' + 'date_field'`. `SELECT_NEWEST` will compare the `date_field` terms, pick the latest, and 
assign it's associated `target_field` to the `destination_field`. In our case, both `target_field` and `date_field` 
are the same field. We want the most recent date from the choice of each column.

We have two categorical destination fields. `occupation_state` takes a `boolean` category, while `occupation_state_reliefs`
requires a list of terms.

`CATEGORISE` has the form: 

```
CATEGORISE > 'destination_field'::'destination_category' 
           < 'source_field'::['source_category', source_category']
```

The `destination_category` can be boolean, and we need to be sure we understand whether the source data defines an 
address as occupied (`True`) or vacant / void (`False`). Getting things the wrong with booleans is a frustratingly 
common curation error.

After this, it all comes together very quickly.

## Transformations with crosswalks

We can now loop through our source schema, assign its corresponding crosswalk and produce transformations:

```python
for key, schema_source in SCHEMA_SOURCE.items():
    # Define a Crosswalk
    crosswalk = qd.CrosswalkDefinition()
    crosswalk.set(schema_source=schema_source, schema_destination=SCHEMA_DESTINATION)
    crosswalk.actions.add_multi(terms=SCHEMA_SCRIPTS[key])
    # Transform a data source
    transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=DATA_SOURCE[key])
    transform.process()
    transform.save(directory=DIRECTORY)
    # Validate a data source
    DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
    TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
    valiform = qd.TransformDefinition()
    valiform.validate(
        transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
    )
```

The default transformation destination data saved mimetype is `parquet`. You can specify something else.

The validation step isn't necessary, but is a sanity check. It will compare the result of your transform by rerunning
the script and comparing the result to your original save destination file.

Despite all this coding and activity, you've actually made no changes to the source data. Everything you've done has 
been about documenting a process. This process is the only thing that will eventually execute and produce your output.

## Preparing a Citation

Research-based data scientists are not always treated well in the research community. Data are hoarded by researchers, 
which also means that the people who produced that data don't get referenced or recognised.

**whyqd** is designed to support a research process and ensure citation of the incredible work done by research-based
data scientists.

A citation is a special set of fields, with options for:

- **author**: The name(s) of the author(s) (in the case of more than one author, separated by `and`),
- **title**: The title of the work,
- **url**: The URL field is used to store the URL of a web page or FTP download. It is a non-standard BibTeX field,
- **publisher**: The publisher's name,
- **institution**: The institution that was involved in the publishing, but not necessarily the publisher,
- **doi**: The doi field is used to store the digital object identifier (DOI) of a journal article, conference paper,
  book chapter or book. It is a non-standard BibTeX field. It's recommended to simply use the DOI, and not a DOI link,
- **month**: The month of publication (or, if unpublished, the month of creation). Use three-letter abbreviation,
- **year**: The year of publication (or, if unpublished, the year of creation),
- **licence**: The terms under which the associated resource are licenced for reuse. It is a non-standard BibTeX field,
- **note**: Miscellaneous extra information.

Let's set up a citation for this tutorial:

```python
citation = {
            "author": "Gavin Chait",
            "month": "feb",
            "year": 2020,
            "title": "Portsmouth City Council normalised database of commercial ratepayers",
            "url": "https://github.com/whythawk/whyqd/tree/master/tests/data",
            "licence": "Attribution 4.0 International (CC BY 4.0)"
        }
transform.set_citation(citation=citation)
```

You can then get your citation report:

```python
transform.get_citation()

{'author': 'Gavin Chait',
'title': 'Portsmouth City Council normalised database of commercial ratepayers',
'url': AnyUrl('https://github.com/whythawk/whyqd/tree/master/tests/data', scheme='https', host='github.com', tld='com', host_type='domain', path='/whythawk/whyqd/tree/master/tests/data'),
'month': 'feb',
'year': 2020,
'licence': 'Attribution 4.0 International (CC BY 4.0)'}
```

Those of you familiar with Dataverse's [universal numerical fingerprint](http://guides.dataverse.org/en/latest/developers/unf/index.html)
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource. Ours is based on 
[BLAKE2b](https://en.wikipedia.org/wiki/BLAKE_(hash_function)) and is included in the data source model saved in the 
transform.

```python
transform.get.dataDestination.checksum

'a8d03afd7d5b93163dac56ba23a7c75dedf42b8999295e560f3d633d54457e9de3ae95dea8181f238e549a7fba10a36723d2f1b1d94ef3f2273129a58bfc0751'
```

## Extending the tutorial

There are three source data schema, but these share a fair number of common fields. They're not ambiguous, either. The
spelling and definitions are identical. You could merge these into one and then any imported datasource could use a
single source schema. You could even work out a way to add source-specific crosswalk scripts algorithmically (I'm 
thinking of the categorical scripts, and the ordering of multi-date fields).

This is left to you as an exercise.