---
title: Create and manage a Schema definition
summary: A data schema describes the structural organisation of tabular data.
authors:
  - Gavin Chait
date: 2023-05-03
tags: wrangling, crosswalks, schema
---
# Create and manage a Schema definition

A **whyqd** (/wɪkɪd/) `schema` definition describes the structural organisation of tabular data. Each column is 
identified by a field name and defined by conformance to technical specifications. These, along with field constraints 
and sensible defaults, ensure interoperability.

In simple terms, the columns in source input data must correspond to the fields defined in your schema. These fields 
may also be reflected as columns in your database, or analytical software. 

If your source data conform to your schema definition, you can develop your software and analysis without any data 
being present. Data validation with your schema are a separate process and permit you to encapsulate each component of 
your project and data management.

!!! abstract "API"
    Review the `class` API definitions: [SchemaDefinition](../api/schema.md) and [CRUDFields](../api/field.md).

## Minimum valid requirements

A minimum valid schema requires a `name` to identify the schema, and a single, minimally-valid `field` containing a 
`name` and `type`:

```json
{
  "name": "A simple name",
  "fields": [
    {
      "name": "Field name, e.g. 'column_name'",
      "type": "Valid data type, e.g. 'string', 'number'"
    }
  ]
}
```

Everything else is optional, unless specifically required by that field-type.

## Schema descriptors

Schema terms include:

### `name`
This is a required term. Spaces will be replaced with `_` and the string will be lowercased.

### `title`
A human-readable version of the schema name.

### `description`
A complete description of the schema. Depending on how complex your work becomes, try and be as helpful as possible to 
'future-you'. You'll thank yourself later.

### `missingValues`
`missingValues` indicates which string values should be treated as null values. There could be a variety of these, such
as '..', or '-'.

### `primaryKey`
A field or set of fields which uniquely identifies each row in the table. Specify using the `name` of relevant fields.

Data in this field will not be tested for uniqueness. Instead, these data will remain immutable, not being 'forced' into 
a date or number type to preserve whatever fruity formatting are described in your input data.

### `index`
Maximum value of a zero-base index for tabular data defined by this schema. Necessary where `actions` apply row-level transforms.

### `citation`
Full citation for definition. More information can be found in the [data source section](datasource.md#citation).

### `version`
Version and update history for the schema. This is automatically generated when you save the definition. It includes a
minimum of `updated` with the date. Can also include a `name` for the person producing the version, and a `description`
of the changes or updates made.

## Field descriptors

Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory. The available types are:

- `string`: Any text-based string (this is the default),
- `number`: Any number-based value, including integers and floats,
- `integer`: Any integer-based value,
- `boolean`: A boolean [true, false] value. Can set category constraints to fix term used,
- `object`: Any valid JSON data,
- `array`: Any valid array-based data,
- `date`: Any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`,
- `datetime`: Any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as 
  `YYYY-MM-DD hh:mm:ss Zz`,
- `year`: Any year, formatted as `YYYY`.

To see all the parameter options for the `SchemaModel`:

```python
import whyqd as qd

qd.models.SchemaModel.schema()

  {'title': 'SchemaModel',
  'type': 'object',
  'properties': {'uuid': {'title': 'Uuid',
  'description': 'Automatically generated unique identity for the schema.',
  'type': 'string',
  'format': 'uuid'},
  'name': {'title': 'Name',
  'description': 'Machine-readable term to uniquely address this schema. Cannot have spaces. CamelCase or snake_case.',
  'type': 'string'},
  'title': {'title': 'Title',
  'description': 'A human-readable version of the schema name.',
  'type': 'string'},
  'description': {'title': 'Description',
  'description': "A complete description of the schema. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
  'type': 'string'},
  'fields': {'title': 'Fields',
  'description': 'A list of fields which define the schema. Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory.',
  'default': [],
  'type': 'array',
  'items': {'$ref': '#/definitions/FieldModel'}},
  'version': {'title': 'Version',
  'description': 'Version and update history for the schema.',
  'default': [],
  'type': 'array',
  'items': {'$ref': '#/definitions/VersionModel'}}},
  'required': ['name'], ...
```

Allowing you to define your initial `schema`:

```python
{
  "name": "urban_population",
  "title": "Urban population",
  "description": "Urban population refers to people living in urban areas as defined by national statistical offices. It is calculated using World Bank population estimates and urban ratios from the United Nations World Urbanization Prospects. Aggregation of urban and rural population may not add up to total population because of different country coverages.",
}
```

### `name`
This is a required term and is equivalent to a column header. It must be defined exactly as it appears in the tabular 
source data.

By convention, this should be *snake_case* with spaces replaced with underscore (e.g. `field_1`), or as *camelCase* with 
linked words capitalised (e.g. `fieldOne`). However, given the range of naming conventions, this can only be a 
recommendation.

### `title`
A human-readable version of the field name.

### `description`
A complete description of the field. As for the schema, try and be as helpful as possible to future-you.

### `dtype` or `type`
`dtype` or `type` defines the data-type of the field. The core supported types:

- `string`: any text-based string.
- `number`: any number-based value, including integers and floats.
- `integer`: any integer-based value.
- `boolean`: a boolean [`true`, `false`] value. Can set category constraints to fix term used.
- `object`: any valid JSON data.
- `array`: any valid array-based data.
- `date`: any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`.
- `datetime`: any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as `YYYY-MM-DD hh:mm:ss Zz`.
- `year`: any year, formatted as `YYYY`.

Since the `type` variable is protected in Python, you'll see it used interchangeably as `type` or `dtype` depending on
the context. To comply with the JSON Schema definitions, JSON outputs will convert the field name to `type`.

### `example`
An example value, as a string, for the field.

## Field constraints

`Constraints` are optional parameters that act as a primary form of validation. Not all of these are available to every 
`type`, and `default_field_settings(type)` will list constraints available to a specific field type.

Define these as part of your schema definition for a specific field:

```python
{
  "name": "indicator_code",
  "title": "Indicator Code",
  "type": "string",
  "description": "World Bank code reference for Indicator Name.",
  "constraints": {"required": True, "unique": True},
}
```

All available constraints:

- `required`: `boolean`, indicates whether this field is compulsory (but blank values in the input column are permitted 
  and will be set to the missing default)
- `unique`: `boolean`, if `True` then all values for that input column must be unique
- `default`: Default category (or string) term used when source values are ambiguous, or unstated.
- `category`: The set of unique category terms permitted in this field,  with `name` & (optional) `description`.
- `minimum`: `integer` / `number`, as appropriate defining min number of characters in a string, or the min values of 
  numbers or integers
- `maximum`: `integer` / `number`, as appropriate defining max number of characters in a string, or the max values of 
  numbers or integers

### `category`

`Category` data are the set of unique category terms permitted in this field. When you define your crosswalk you can
define values which should be assigned to each of these categories.

In [JSON Schema](https://json-schema.org/), this is called `enum`. In the `whyqd` API, you will refer to `.category` to 
reference the list of categories. However, in the json output files, these will be referenced as `enum` for compliance
with the standard.

Define these as part of your schema definition for a specific field:

```python
{
  "name": "test_field",
  "type": "string",
  "constraints": {
    "required": True,
    "category": [
      {"name": "dog", "description": "A type of mammal"},
      {"name": "cat", "description": "A different type of mammal"},
      {"name": "mouse", "description": "A small type of mammal"},
    ],
    "default": {"name": "dog", "description": "A type of mammal"},
  },
}
```

Each `category` can have a `name`, and a `description`, but the minimum is a `name`.

Each field `type` will have its own category constraints. For example, boolean categories can use a different term than 
True / False defined by the category, but only permits two terms. Others have a minimum of one term in a category, but 
require the list member type to be `string`, `number`, etc. Ordinarily, `category` terms must be unique.

## Creating a Schema

The objective of your schema is not only to define a structure for your data, but also provide reference and contextual 
information for anyone using it. In a research context, definitions are critical to avoid ambiguity, ensure replication, 
and build trust.

You can import a schema definition from a file, or you can build it interactively, as shown here. We'll start by 
importing **whyqd** and defining a new schema.

The minimum requirement for a schema is that it have a `name`, but we're going to give it a `title` and `description` 
as well, because more information is better. We're not barbarians:

```python
import whyqd as qd

schema: qd.models.SchemaModel = {
    "name": "urban_population",
    "title": "Urban population",
    "description": "Urban population refers to people living in urban areas as defined by national statistical offices.",
}
schema_destination = qd.SchemaDefinition()
schema_destination.set(schema=schema)
```
We can also save our schema to a specified `directory`:

```python
directory = "/path/to/directory"
filename = "urban_population_2020"
schema.save(directory=directory, filename=filename, created_by="Gavin Chait")
```

If the optional `filename` is not provided, the name you specified in the `schema` dictionary will be used. The file is 
a JSON format text file, but will have the extension `.schema`. A version history will be automatically created, and you 
can add your name as `created_by`.

We'll now start to create each of our schema `fields`.

!!! info
    You can think of a schema `field` as a `column` in a table, or a `field` in a database. Each field, unsurprisingly, 
    has a `name`, `title` and `description`, of which only the `name` is required.
    
    Fields have a `type`, such as `number` or `string`. This describes the data expected and limits the actions which 
    can be performed during the wrangling process

We want our destination data to conform to the following structure:

| la_code  | ba_ref       | occupant_name | postcode | occupation_state | occupation_state_date | prop_ba_rates | occupation_state_reliefs |
|:---------|:-------------|:--------------|:-------- |:-----------------|:----------------------|:--------------|:-------------------------|
|E06000044 | 177500080710 | A company     | PO5 2SE  | True             | 2019-04-01            | 98530         | [small_business, retail] |

We'll build a single dictionary and then iterate over the list to add each field:

```python
import whyqd as qd

schema: qd.models.SchemaModel = {
    "name": "rates_data",
    "title": "Commercial rates data",
    "description": "Standardised schema for archival and analysis of commercial / non-domestic rates data.",
}
fields: list[qd.models.FieldModel] = [
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
schema_destination = qd.SchemaDefinition()
schema_destination.set(schema=schema)
schema_destination.fields.add_multi(terms=fields)
```

You could also `add`:

```python
for field in fields:
  schema_destination.fields.add(term=field)
```

From here on we can access any `field` by calling it by `name` and then updating it as required:

```python
schema_destination.fields.get(name="occupation_state_reliefs")

	{'name': 'occupation_state_reliefs',
	 'type': 'array',
	 'title': 'Occupation state reliefs',
	 'description': 'Array of the categories of reliefs / exemptions applied.'}
```

Let's add a list of `category` terms as a constraint for `occupation_state_reliefs`:

```python
categories = ["small_business", "rural", "charity", "enterprise_zone", "vacancy", "hardship", "retail", "discretionary", "exempt", "transitional", "other"]
constraints = {
    "category": [
      { "name": category } for category in categories
    ]
  }
schema_destination.fields.set_constraints(name="occupation_state_reliefs", constraints=constraints)
schema_destination.fields.get(name="occupation_state_reliefs").model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)

  {'uuid': UUID('cf4d066e-22a8-4b76-8956-f6120eec4c52'),
  'name': 'occupation_state_reliefs',
  'title': 'Occupation state reliefs',
  'description': 'Array of the categories of reliefs / exemptions applied.',
  'type': 'array',
  'constraints': {'enum': [{'uuid': UUID('daa206a9-ac8c-41a9-a504-06410780ee50'),
    'name': 'small_business'},
  {'uuid': UUID('5964e9fc-dd50-4856-acdc-2326ea48ef1d'), 'name': 'rural'},
  {'uuid': UUID('498654f9-8825-4f3d-a573-0c110726fba4'), 'name': 'charity'},
  {'uuid': UUID('f94353ce-a489-4fb1-ad78-5435b3dd54a4'),
    'name': 'enterprise_zone'},
  {'uuid': UUID('41285fc0-2321-4542-b7f1-e8e535588559'), 'name': 'vacancy'},
  {'uuid': UUID('28068ff2-15ff-409a-9a8f-f97c39407812'), 'name': 'hardship'},
  {'uuid': UUID('b8041d21-f8ca-47b9-b3fe-7b9077388459'), 'name': 'retail'},
  {'uuid': UUID('83bda0d4-3d94-4738-a580-cfe0881c8e4d'),
    'name': 'discretionary'},
  {'uuid': UUID('ff2cbc0c-839b-430c-bdca-ac4238634f05'), 'name': 'exempt'},
  {'uuid': UUID('f4300571-c04b-4cbf-b835-16c5ae3343b0'),
    'name': 'transitional'},
  {'uuid': UUID('8a3af6f4-f48c-4614-83f2-ba472b2129e9'), 'name': 'other'}]}}
```

The term `.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)` is used to extract a dictionary format from 
the underlying [Pydantic](https://pydantic-docs.helpmanual.io/) model used by `whyqd`.

!!! info
    These are the official business [rates reliefs](https://www.gov.uk/apply-for-business-rate-relief) permitted by the 
    UK government. Unsurprisingly, only by accident do any local authorities actually use these terms when awarding a 
    relief.

Review your schema, then `save` and we're ready to begin schema-to-schema conversion:

```python
schema_destination.get.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)

	{'uuid': UUID('19692345-2caf-46b1-9a8f-276491520c6b'),
	'name': 'test_schema',
	'title': 'Test Schema',
	'description': 'A test Schema',
	'fields': [{'uuid': UUID('615d2cd0-f8b6-4449-b3d2-642fa4836888'),
	'name': 'la_code',
	'title': 'Local authority code',
	'description': 'Standard code for local authority.',
	'type': 'string',
	'constraints': {'default': {'uuid': UUID('579342cd-bba8-41cd-bf45-3c517b8cd75e'),
		'name': 'E06000044'}}},
	{'uuid': UUID('95f5c53c-59e1-4bb7-917d-7177b01d2d3c'),
	'name': 'ba_ref',
	'title': 'Billing reference',
	'description': 'Unique code for a specific hereditament. May be multiple rows for history.',
	'type': 'string'},
	{'uuid': UUID('7572ae3e-d725-4897-84fb-5c5b45bd4edb'),
	'name': 'prop_ba_rates',
	'title': 'Property billing rates',
	'description': 'Actual rates paid by a specific ratepayer.',
	'type': 'number'},
	{'uuid': UUID('ac76c3ab-5ef8-4641-99ec-aab2c5b7414c'),
	'name': 'occupant_name',
	'title': 'Occupier name',
	'description': 'Name of the ratepayer.',
	'type': 'string'},
	{'uuid': UUID('26440eba-fd1d-40af-a52c-a9351fad2fd9'),
	'name': 'postcode',
	'title': 'Postcode',
	'description': 'Full address or postcode of ratepayer.',
	'type': 'string'},
	{'uuid': UUID('28d7863b-22fa-4bd5-a221-0607643f0111'),
	'name': 'occupation_state',
	'title': 'Occupation state',
	'description': 'Occupation status, void or occupied.',
	'type': 'boolean',
	'constraints': {'enum': [{'uuid': UUID('353bd4ac-d677-47c4-af40-6f651af2cc5e'),
		'name': True},
		{'uuid': UUID('33f8b2f8-9ac5-412a-9507-879bb7f845ce'), 'name': False}],
		'default': {'uuid': UUID('353bd4ac-d677-47c4-af40-6f651af2cc5e'),
		'name': True}}},
	{'uuid': UUID('79a70822-4e24-4a68-9036-992def200cd6'),
	'name': 'occupation_state_date',
	'title': 'Date of occupation state',
	'description': 'Date of the start of status in occupation_state.',
	'type': 'date'},
	{'uuid': UUID('cf4d066e-22a8-4b76-8956-f6120eec4c52'),
	'name': 'occupation_state_reliefs',
	'title': 'Occupation state reliefs',
	'description': 'Array of the categories of reliefs / exemptions applied.',
	'type': 'array',
	'constraints': {'enum': [{'uuid': UUID('daa206a9-ac8c-41a9-a504-06410780ee50'),
		'name': 'small_business'},
		{'uuid': UUID('5964e9fc-dd50-4856-acdc-2326ea48ef1d'), 'name': 'rural'},
		{'uuid': UUID('498654f9-8825-4f3d-a573-0c110726fba4'), 'name': 'charity'},
		{'uuid': UUID('f94353ce-a489-4fb1-ad78-5435b3dd54a4'),
		'name': 'enterprise_zone'},
		{'uuid': UUID('41285fc0-2321-4542-b7f1-e8e535588559'), 'name': 'vacancy'},
		{'uuid': UUID('28068ff2-15ff-409a-9a8f-f97c39407812'),
		'name': 'hardship'},
		{'uuid': UUID('b8041d21-f8ca-47b9-b3fe-7b9077388459'), 'name': 'retail'},
		{'uuid': UUID('83bda0d4-3d94-4738-a580-cfe0881c8e4d'),
		'name': 'discretionary'},
		{'uuid': UUID('ff2cbc0c-839b-430c-bdca-ac4238634f05'), 'name': 'exempt'},
		{'uuid': UUID('f4300571-c04b-4cbf-b835-16c5ae3343b0'),
		'name': 'transitional'},
		{'uuid': UUID('8a3af6f4-f48c-4614-83f2-ba472b2129e9'),
		'name': 'other'}]}}]}

schema_destination.save(directory=directory, filename=filename, created_by="Gavin Chait")
```

Whyqd's [data source strategies](datasource.md) show you how to derive a schema to reflect source data.