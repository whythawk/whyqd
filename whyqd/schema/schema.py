"""
.. module:: schema
   :synopsis: Create and manage a target data schema.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Schema
======

Creating a `schema` is the first part of the wrangling process. Your schema defines the structural
metadata target for your wrangling process. This is not the format your input data arrive in, but
it is what you require it to look like when you're done.

Your schema sets the requirements, constraints and sensible defaults available for creating each
`method` that will describe the process for wrangling input data into the fields defined by the
schema. It can be reused to create multiple `methods`. Once complete, automated scripts can perform
further cleaning and validation.

In simple terms, the columns in an input CSV or Excel-file will be restructured into new columns
defined by the fields in your schema. These target fields are likely to be those in your database,
or in your analytical software. Until your input data conform to this structure, you can't do your
real work.

Minimum valid requirements
--------------------------

A minimum valid schema requires a `name` to identify the schema, and a single, minimally-valid
`field` containing a `name` and `type`::

    {
        "name": "A simple name",
        "fields": [
        {
            "name": "Field name, e.g. 'column_name'",
            "type": "Valid data type, e.g. 'string', 'number'"
        }
        ]
    }

Everything else is optional, unless specifically required by that field-type.

Schema descriptors
------------------

Schema terms include:

`name`
^^^^^^
This is a required term. Spaces will be replaced with `_` and the string will be lowercased.

`title`
^^^^^^^
A human-readable version of the schema name.

`description`
^^^^^^^^^^^^^
A complete description of the schema. Depending on how complex your work becomes, try and be as
helpful as possible to 'future-you'. You'll thank yourself later.

Field descriptors
-----------------

Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory. To
see the available field types::

    >>> sc = _d.Schema()
    >>> sc.default_field_types
    ['string',
    'number',
    'integer',
    'boolean',
    'object',
    'array',
    'date',
    'datetime',
    'year']

To see further parameter options for each default type::

    >>> sc.default_field_settings('string')
    {
        'required': ['name', 'type'],
        'name': 'field_name',
        'title': 'A human-readable version of the field name',
        'description': 'Any text-based string.',
        'type': 'string',
        'format': {
            'description': 'The format keyword options for `string` are `default`, `email`, `uri`, `binary`, and `uuid`.',
            'category': ['default', 'email', 'uri', 'binary', 'uuid'],
            'default': 'default'
            },
        'foreignKey': {
            'type': 'boolean',
            'description': 'Set `foreignKey` `true` if the field is to be treated as an immutable value.'
            },
        'constraints': {
            'description': 'The following constraints are supported.',
            'properties': {
                'required': {
                    'type': 'boolean',
                    'description': 'Indicates whether a property must have a value for each instance.'
                },
                'unique': {
                    'type': 'boolean',
                    'description': 'When `true`, each value for the property `MUST` be unique.'
                },
            'category': {
                'type': 'array',
                'minItems': 1,
                'uniqueItems': True,
                'terms': {
                    'type': 'string'
                    }
                },
            'minimum': {
                'type': 'integer',
                'description': 'An integer that specifies the minimum length of a value.'
                },
            'maximum': {
                'type': 'integer',
                'description': 'An integer that specifies the maximum length of a value.'
                }
            }
        },
    'missing': {
        'description': 'Default to be used for missing values.',
        'default': ''
        }
    }

`name`
^^^^^^
This is a required term and is equivalent to a column header. Spaces will be replaced with `_` and
the string will be lowercased.

`title`
^^^^^^^
A human-readable version of the field name.

`description`
^^^^^^^^^^^^^
A complete description of the field. As for the schema, try and be as helpful as possible to
future-you.

`foreignKey`
^^^^^^^^^^^^
This is a boolean term, only required if you need this field to be treated as a foreign-key or
identifier for your destination data::

    "foreignKey": True

Data in this field will not be tested for uniqueness. Instead, these data will remain immutable, not
being 'forced' into a date or number type to preserve whatever fruity formatting are described in
your input data.

During the wrangling process, this field can be used for merging with other input
data, ensuring consistency between sources.

`type` and `format`
^^^^^^^^^^^^^^^^^^^
`type` defines the data-type of the field, while `format` - which is currently unsupported in
wrangling - further refines the specific `type` properties. The core supported types, with indents
for formats:

* `string`: any text-based string.

  * `default`: any string
  * `email`: an email address
  * `uri`: any web address / URI

* `number`: any number-based value, including integers and floats.
* `integer`: any integer-based value.
* `boolean`: a boolean [`true`, `false`] value. Can set category constraints to fix term used.
* `object`: any valid JSON data.
* `array`: any valid array-based data.
* `date`: any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`.
* `datetime`: any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as `YYYY-MM-DD hh:mm:ss Zz`.
* `year`: any year, formatted as `YYYY`.

`missing`
^^^^^^^^^
`missing` defines the value to be used for any blank values in a column. This is normally `""` for
text and `np.nan` for numbers or dates. You can, however, set your own defaults for each field.

Field constraints
-----------------
`Constraints` are optional parameters that refine input data wrangling and act as a primary form of
validation. Not all of these are available to every `type`, and `default_field_settings(type)`
will list constraints available to a specific field type.

Define these as part of your schema definition for a specific field::

    {
      "name": "A simple name",
      "fields": [
        {
            "name": "Field name, e.g. 'column_name'",
            "type": "Valid data type, e.g. 'string', 'number'",
            "constraints": {
                "required": True,
                "unique": True
            }
        }
      ]
    }

All available constraints:

* `required`: boolean, indicates whether this field is compulsory (but blank values in the input column are permitted and will be set to the `missing` default)
* `unique`: boolean, if `true` then all values for that input column must be unique
* `minimum`: `integer` / `number`, as appropriate defining min number of characters in a string, or the min values of numbers or integers
* `maximum`: `integer` / `number`, as appropriate defining max number of characters in a string, or the max values of numbers or integers

Field constraints: category
---------------------------
In FrictionlessData.io, this is called `enum`, which isn't particularly meaningful. `Category` data
are the set of unique category terms permitted in this field. During wrangling you will be able to
define values which should be assigned to each of these categories.

Define these as part of your schema definition for a specific field::

    {
      "name": "A simple name",
      "fields": [
        {
            "name": "Field name, e.g. 'column_name'",
            "type": "Valid data type, e.g. 'string', 'number'",
            "constraints": {
                "category": ["cheddar", "gouda", "other"]
            }
        }
      ]
    }

Each field `type` will have its own category constraints. For example, boolean categories can use a
different term than True / False defined by the category, but only permits two terms. Others have
a minimum of one term in a category, but require the list member type to be `string`, `number`, etc.
Ordinarily, `category` terms must be unique.

Review the `default_field_settings(type)` for that field's specific category constraints.

Field constraints: filter
--------------------------
`Filters` are a constraint that filter a named field, or the `foreignKey`, by date-limited data.

Define these as part of your schema definition for a valid field::

    {
      "name": "A simple name",
      "fields": [
        {
            "name": "Field name, e.g. 'column_name'",
            "type": "Valid data type, e.g. 'date', 'datetime'",
            "filter": {
                "field": "foreignKey",
                "modifiers": ["LATEST", "AFTER"]
            }
        }
      ]
    }

There are two compulsory parameters defining a filter:

* `field`: another field which is the subject of this filter, or by default the 'foreignKey'.
* `modifiers`: an array of permitted filter terms, including any of ["LATEST", "AFTER", "BEFORE", "ALL"].

call `default_filter_names()` to get a list, and `default_filter_settings(filter_name)` to get a
definition

For example, to filter all foreign keys (which may be duplicated as part of a time-series) to be
more recent than a specified date, include "AFTER" in your list of filter modifiers.
"""

from typing import Optional, Union
from pydantic import Json

from .models import SchemaModel, FieldModel, ConstraintModel, VersionModel
from whyqd.core import common as _c


class Schema:
    """Create and manage a target schema for a wrangling process.

    Parameters
    ----------
    source: str, optional
        Path to a json file containing a saved schema, default is None.
    schema: SchemaModel, optional
        A dictionary conforming to the SchemaModel, default is None.
    """

    def __init__(self, source: Optional[str] = None, schema: Optional[SchemaModel] = None):
        # self.default_filters = _c.get_settings("filter")
        self._schema = None
        if source:
            self._schema = SchemaModel(**_c.load_json(source))
        if schema:
            self.set(schema)

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self._schema:
            return f"Schema: `{self._schema.name}`"
        return "Schema"

    @property
    def describe(self) -> dict[str, None]:
        """Get the schema name, title and description.

         - name: Term used for filename and referencing. Will be lower-cased and spaces replaced with `_`
         - title: Human-readable term used as name.
         - description: Detailed description for the schema. Reference its objective and use-case.

        Returns
        -------
        dict or None
        """
        if self._schema:
            response = {
                "name": self._schema.name,
                "title": self._schema.title,
                "description": self._schema.description,
            }
            return response
        return None

    @property
    def get(self) -> Union[SchemaModel, None]:
        """Get the schema model.

        Returns
        -------
        SchemaModel or None
        """
        return self._schema

    @property
    def get_json(self) -> Union[Json, None]:
        """Get the json schema model.

        Returns
        -------
        Json or None
        """
        if self._schema:
            return self._schema.json(by_alias=True, exclude_defaults=True, exclude_none=True)
        return None

    def set(self, schema: SchemaModel):
        """Update or create the schema.

        Parameters
        ----------
        schema: SchemaModel
            A dictionary conforming to the SchemaModel.
        """
        # Create a temporary SchemaModel
        updated_schema = SchemaModel(**schema)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self._schema:
            self._schema = self._schema.copy(update=updated_schema.dict(exclude_unset=True))
        else:
            self._schema = updated_schema

    def get_field(self, name: str) -> Union[FieldModel, None]:
        """Get a specific field from the list of fields defining this schema, called by a unique `name`.

        Parameters
        ----------
        name: string
            Field names must be unique, so a valid `name` in the field list will have no collisions.

        Returns
        -------
        FieldModel, or None if no such `name`
        """
        if self._schema:
            # https://stackoverflow.com/a/31988734/295606
            return next((f for f in self._schema.fields if f.name == name), None)
        return None

    def add_field(self, field: FieldModel):
        """Add the parameters for a specific field, called by a unique `name`.
        If the `name` already exists, then this will raise a ValueError.

        Parameters
        ----------
        field: FieldModel
            A dictionary conforming to the FieldModel.

        Raises
        ------
        ValueError: if field already exists.
        """
        new_field = FieldModel(**field)
        if self.get_field(new_field.name):
            raise ValueError(f"FieldModel {new_field.name} already exists in the schema.")
        self._schema.fields.append(new_field)

    def remove_field(self, name: str):
        """Remove a specific field, called by a unique `name`.

        Parameters
        ----------
        kwargs: FieldModel
            A dictionary conforming to the FieldModel.
        """
        # https://stackoverflow.com/a/1235631/295606
        self._schema.fields[:] = [f for f in self._schema.fields if f.name != name]

    def set_field(self, field: FieldModel):
        """Update the parameters for a specific field, called by a unique `name`.
        If the `name` does not exist, then this will raise a ValueError.

        Parameters
        ----------
        field: FieldModel
            A dictionary conforming to the FieldModel.

        Raises
        ------
        ValueError: if field does not exist
        """
        # Create a temporary FieldModel
        new_field = FieldModel(**field)
        old_field = self.get_field(new_field.name)
        if not old_field:
            raise ValueError(f"FieldModel {new_field.name} does not exist in the schema.")
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        old_field = old_field.copy(update=new_field.dict(exclude_unset=True))
        self.remove_field(new_field.name)
        self.add_field(old_field.dict(by_alias=True, exclude_defaults=True, exclude_none=True))

    def get_field_constraints(self, name: str) -> Union[ConstraintModel, None]:
        """Get the constraint parameters for a specific field defined in this schema, called by a unique
        `name` already in the schema.

        Parameters
        ----------
        name: string
                Specific name for a field already in the Schema

        Returns
        -------
        ConstraintModel or None
        """
        field = self.get_field(name)
        if not field:
            raise ValueError(f"FieldModel {name} does not exist in the schema.")
        return field.constraints

    def set_field_constraints(self, name: str, constraints: Union[ConstraintModel, None]):
        """Set the constraint parameters for a specific field to define this schema, called by a unique
        `name` already in the schema.

        Parameters
        ----------
        name: string
            Specific name for a field already in the Schema
        constraints: ConstraintModel or None
            A dictionary conforming to the ConstraintModel, or None. If None, then constraints are deleted.
        """
        old_constraints = self.get_field_constraints(name)
        if not constraints:
            old_constraints = None
        else:
            new_constraints = ConstraintModel(**constraints)
            if old_constraints:
                old_constraints = old_constraints.copy(update=new_constraints.dict(exclude_unset=True))
            else:
                old_constraints = new_constraints
        self.get_field(name).constraints = old_constraints

    def save(
        self,
        directory: str,
        filename: Optional[str] = None,
        overwrite: Optional[bool] = False,
        created_by: Optional[str] = None,
    ) -> bool:
        """Save schema as a json file.

        Parameters
        ----------
        directory: strthe destination directory
        filename: defaults to schema name
        overwrite: bool, True if overwrite existing file
        created_by: string, or None, to define the schema creator/updater

        Returns
        -------
        bool True if saved
        """
        if not self._schema:
            raise ValueError("Schema does not exist.")
        if not filename and self._schema:
            filename = self._schema.name
        if filename.split(".")[-1] != "json":
            filename += ".json"
        update = VersionModel()
        if created_by:
            update.name = created_by
        self._schema.version.append(update)
        return _c.save_file(self.get_json, directory + filename, overwrite)
