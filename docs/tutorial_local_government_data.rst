Tutorial: Local government data
===============================
**whyqd** was developed to solve a daily, grinding need in our `Sqwyre.com <https://sqwyre.com>`_
project. *Sqwyre* is an online market intelligence service helping you assess opportunities and risks 
for every commercial property in England and Wales. Every quarter, we import about 300 very messy 
spreadsheets from local authorities across the UK. These need to be restructured to conform to a 
single schema, including redefining whatever weird terms they use to describe categorical data, and 
only then can we begin the automated process of cleaning and validation. It's a mostly free
service, so you can see it in action at `Sqwyre.com <https://sqwyre.com>`_.

When we started, this was a purely manual process but, gradually, we developed what has become
**whyqd**. The process, at a high level, is as follows:

  - Create, update or import a data schema which defines the destination data structure,
  - Create a new method and associate it with your schema and input data source/s,
  - Assign a foreign key column and (if required) merge input data sources,
  - Define actions to restructure and assign categorical definitions,
  - Filter and transofrm input data to produce a final restructured data file.

You are more likely to create your schema at the beginning of a project, and then spend most of your
time using that schema as the base for creating new methods for each new data source. If you're really
lucky, your data source won't change their methods from release-to-release and you can reuse your
own. In our experience that is like searching for unicorns.

The example in our worked tutorial is derived directly from our workflow at Sqwyre.com and is from a
dataset released by `Portsmouth City Council <https://www.portsmouth.gov.uk/ext/business/running-a-business/business-rates-foi-requests>`_.
The data in this tutorial are from January 2020, but follow along with the current download.

.. note:: This tutorial does assume familiarity with Python and Pandas, and Pydantic for type annotations.

Creating a Schema
-----------------
Review the :doc:`schema` documentation for more details. We'll start by importing **whyqd**
and defining a new schema::

    >>> import whyqd
    >>> schema = whyqd.Schema()

The objective of your schema is not only to define a structure for your data, but also provide
reference and contextual information for anyone using it. In a research context, definitions are
critical to avoid ambiguity, ensure replication, and build trust.

The minimum requirement for a schema is that it have a `name`, but we're going to give it a `title`
and `description` as well, because more information is better. We're not barbarians::

    >>> details = {
			"name": "rates_data_schema",
			"title": "UK Ratepayer data schema",
			"description": "Structural metadata target for imported messy data from the 348 local authorities in England & Wales."
		}
    >>> schema.set(details)

We can also save our schema to a specified `directory`::

    >>> directory = "/path/to/directory"
    >>> filename = "2020_rates_data_schema"
    >>> schema.save(directory, filename=filename, created_by="Gavin Chait")

'filename' is optional, and the name you specified in the `details` dictionary will be used instead. A version history
will be automatically created, and you can add your name as `created_by`.

We'll now start to create each of our schema `fields`.

.. note:: You can think of a schema `field` as a `column` in a table, or a `field` in a database. 
	Fields have a `type`, such as integer or text.

Each field, unsurprisingly, has a `name`, `title` and `description`, of which only the `name` is required.
Fields also have a `type`. This describes the data expected and limits the actions which can be performed
during the wrangling process.

We want our destination data to conform to the following structure:

=========  ============  =============  ========  ================  =====================  =============  ========================
la_code    ba_ref        occupant_name  postcode  occupation_state  occupation_state_date  prop_ba_rates  occupation_state_reliefs
=========  ============  =============  ========  ================  =====================  =============  ========================
E06000044  177500080710  A company       PO5 2SE              True             2019-04-01          98530  [small_business, retail]
=========  ============  =============  ========  ================  =====================  =============  ========================

Each of these fields is a different `type` of data:

* `string`: any text-based string.
* `number`: any number-based value, including integers and floats.
* `integer`: any integer-based value.
* `boolean`: a boolean [`true`, `false`] value. Can set category constraints to fix term used.
* `object`: any valid JSON data.
* `array`: any valid array-based data.
* `date`: any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`.
* `datetime`: any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as 
  `YYYY-MM-DD hh:mm:ss Zz`.
* `year`: any year, formatted as `YYYY`.

In addition, these data can be `constrained`:

* `required`: boolean, indicates whether this field is compulsory (but blank values in the input column 
  are permitted and will be set to the `missing` default),
* `unique`: boolean, if `true` then all values for that input column must be unique,
* `minimum`: `integer` / `number`, as appropriate defining min number of characters in a string, or 
  the min values of numbers or integers,
* `maximum`: `integer` / `number`, as appropriate defining max number of characters in a string, or 
  the max values of numbers or integers,
* `category`: the set of unique category terms permitted in this field,
* `default`:  a default category term to use where no information is given.

We'll go through most of these in the tutorial. Note that some of these are only there to support
post-wrangling (such as `minimum` or `maximum`). `required` means that a method won't be validated
if that field has no data.

We'll build a single dictionary and then iterate over the list to add each field::

    >>> fields = [
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
    >>> for field in fields:
	...		schema.add_field(field)

From here on we can access any `field` by calling it by `name` and then updating it as required::

    >>> schema.get_field("occupation_state_reliefs")
	{'name': 'occupation_state_reliefs',
	 'type': 'array',
	 'title': 'Occupation state reliefs',
	 'description': 'Array of the categories of reliefs / exemptions applied.'}

Let's add a list of `category` terms as a constraint for `occupation_state_reliefs`::

    >>> categories = ["small_business", "rural", "charity", "enterprise_zone", "vacancy", "hardship", "retail", "discretionary", "exempt", "transitional", "other"]
	>>> constraints = {
			"categories": [{
				"name": category for category in categories
			}]
		}
    >>> schema.set_field_constraints(field="occupation_state_reliefs", category=constraints)
    >>> schema.get_field("occupation_state_reliefs").dict(by_alias=True, exclude_defaults=True, exclude_none=True)
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

The term `.dict(by_alias=True, exclude_defaults=True, exclude_none=True)` is used to extract a dictionary format from
the underlying `Pydantic <https://pydantic-docs.helpmanual.io/>`_ model used by `whyqd`.

.. note:: These are the official business `rates reliefs <https://www.gov.uk/apply-for-business-rate-relief>`_
	permitted by the UK government. Unsurprisingly, only by accident do any local authorities actually 
	use these terms when awarding a relief.

We could choose to limit the `filter` field for the `occupation_state_date`, but we're not going to
bother. Review your schema, then `save` and we're ready to begin wrangling::

    >>> schema.get.dict(by_alias=True, exclude_defaults=True, exclude_none=True)
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

    >>> schema.save(directory, filename=filename, created_by="Gavin Chait")

Creating a Method
-----------------
**whyqd** can import any of CSV, XLS or XLSX files, but do check that these files actually open and
are readable before proceeding. You'll be surprised at the number of supposedly open datasets
released with password-protection, fruity formatting, or which are completely corrupted.

.. warning:: The minimum required to ensure a dataset is machine-readable is that it opens in `pandas`.

In our tutorial example, the data from `Portsmouth City Council <https://www.portsmouth.gov.uk/ext/business/running-a-business/business-rates-foi-requests>`_
include three Excel (XLS) data files:

* `NDR properties January 2020`
* `NDR reliefs January 2020`
* `Empty commercial properties January 2020`

Apologies for not linking, but these are not persistent URIs. Keep that in mind in the code that
follows.

Initialise a Method and import input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The only compulsory parameter needed when creating a method, is a reference to our source schema
(the one we created above). We may also offer a working directory. During the process, **whyqd** will
create a number of interim working data files, as well as your JSON method file, and your wrangled
output data. You need to tell it where to work, or it will simply drop everything into the
directory you're calling the function from.

We can also provide the list of data sources::

    >>> import whyqd
    >>> SCHEMA_SOURCE = "/full/path_to/2020_rates_data_schema.json"
    >>> DIRECTORY = "/path_to/working/directory/"
	# Note: these links may no longer work when you follow this tutorial. Get the latest ones...
    >>> INPUT_DATA = [
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls",
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls",
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls"
    >>> method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
    >>> method.add_data(source=INPUT_DATA)

These data will be copied to your working directory and renamed to a unique `uuid` and assigned a unique hashed
`checksum`.

.. note:: **Data probity** - the abilty to audit data and methodology back to source - is critical for 
	research transparency and replication. You may end up with hundreds of similarly-named files in a 
	single directory without much information as to where they come from, or how they were created. 
	Unique ids, referenced in your method file, are a more useful way of ensuring you know what they 
	were for.

Organise and Merge input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We have three input data files. These need to be consolidated into a single working data file via a
merge. **whyqd** will iteratively join files in a list, adding the 2nd to the 1st, then the 3rd, etc.

What we need to do is decide on the order, and identify a column that can be used to uniquely
cross-reference rows in each file and link them together.

Remember the original source file names:

* `NDR properties January 2020`
* `NDR reliefs January 2020`
* `Empty commercial properties January 2020`

You'll have to take my word for it, but that is a reasonable order, so we're good. We do need to
identify the merge columns. Each property has a unique (for a given order of "unique" ... local
government, mutter mutter) id, usually called some variation of "Property Reference". Let's create
our `order_and_key` dict and then merge (and your reference ids will be different)::

    >>> merge_reference = [
		{"source_hex": method.get.input_data[0].uuid.hex, "key_column": "Property ref no"},
		{"source_hex": method.get.input_data[1].uuid.hex, "key_column": "Property Reference Number"},
		{"source_hex": method.get.input_data[2].uuid.hex, "key_column": "Property Reference Number"},
        ]
    >>> merge_terms = ", ".join([f"'{m['key_column']}'::'{m['source_hex']}'" for m in merge_reference])
    >>> merge_script = f"MERGE < [{merge_terms}]"
    >>> method.merge(merge_script)

Since this is `pandas` underneath, you may get a `UserWarning` like this::

	UserWarning: '3b2e9893-c04c-4714-b9bb-6dd2bf274db4.xls' contains non-unique rows in column `Property Reference Number`
	UserWarning: '458d7c0b-1481-487e-b120-19ccd2326d24.xls' contains non-unique rows in column `Property Reference Number`

OK, what does that `warning` mean?

This is where we need a brief digression into the use of `data as a science <https://github.com/whythawk/data-as-a-science/>`_.

Underneath **whyqd** is `pandas <https://pandas.pydata.org/>`_. A merge in a pandas dataframe will
join the first of two rows. Any subsequent rows with a similar unique id will be added at the bottom
(either 'left' or 'right', depending on the merge source), but orphaned. We can deal with this
problem in a number of ways, but let's go back and look at the source data.

Each of our sources comes with most of the fields we want to populate our target schema. We can 'fix'
these orphaned rows in post. However, what happens if we couldn't? That depends and requires you to
have an indepth knowledge of your data source and research requirements. You may want to filter
your source data in advance (i.e. create an interim schema and wrangle these data in as well).

Wrangling your input data sounds like you needed an interim schema and method. Your objective is a
readable, auditable method. Don't try and do too much in one go. Work methodically to ensure you're
clear on what you're doing at each step rather than getting all recursive in your methods.

Create wrangling actions
^^^^^^^^^^^^^^^^^^^^^^^^
This is the part of the wrangling process where, depending on the scale of what you're up to, you
reach for Excel, `OpenRefine <https://openrefine.org/>`_ or some commercial alternative. These are
sometimes outside of your workflow, or introduce (hello Excel) the potential for human error.

Options like OpenRefine are great, but are quite heavy. They're useful if you're performing all
your wrangling in one place (including dealing with row-level value errors), but it's a fairly
heavy investment in that system's language and approach. On the other hand, if you're already used
to using pandas and Python for dealing with these post-wrangling validation errors, then **whyqd**
offers:

* Simplicity: you already know Python, and - as you'll see - not much is required to wire up a munge.
* Transparency: you'll get a full audit trail in a readable JSON file.
* Speed: hopefully you'll get a sense of that through this tutorial.

Critically, **whyqd** is for *repeatable* and **auditable** processing. Next quarter, Portsmouth will update their data
and we want to import it again. However, it probably won't be in the same format as this quarter
since a human being prepared and uploaded these data. That person doesn't know about your use-case
and probably doesn't care (at least they haven't accused you of `promoting terrorism <http://informationrights.decisions.tribunals.gov.uk/DBFiles/Decision/i2557/Westminster%20City%20Council%20EA-2018-0033%20(04.12.19).pdf>`_
with these data). Maybe they change some column names. The URI will definitely be different, and maybe
so will the file order. These are simple changes and all that's required is a minor adjustment to the
method to run this process again.

Every task structure must start with an action to describe what to do with the following terms.
There are several "actions" which can be performed, and some require action modifiers:

* NEW: Add in a new column, and populate it according to the value in the "new" constraint

* RENAME: If only 1 item in list of source fields, then rename that field

* ORDER: If > 1 item in list of source fields, pick the value from the column, replacing each 
  value with one from the next in the order of the provided fields

* ORDER_NEW: As in ORDER, but replacing each value with one associated with a newer "dateorder" 
  constraint:

  * MODIFIER: `+` between terms for source and source_date

* ORDER_OLD: As in ORDER, but replacing each value with one associated with an older "dateorder" 
  constraint:

  * MODIFIER: `+` between terms for source and source_date

* CALCULATE: Only if of `type` = `float64` (or which can be forced to float64):

  * MODIFIER: `+` or `-` before each term to define whether add or subtract

* JOIN: Only if of `type` = `object`, join text with `" ".join()`

* CATEGORISE: Only if of `type` = `string`; look for associated constraint, `categorise` where 
  `True` = keep a list of categories, `False` = set `True` if terms found in list:

  * MODIFIER:

    * `+` before terms where column values to be classified as unique

    * `-` before terms where column values are treated as boolean

This tutorial doesn't require you to do all of these, but it gives you a good flavour of use. You
can also nest actions, but use common sense to ensure you know what the result is likely to be.

.. note:: if you're not quite sure what a set of actions will do, run it and see. **whyqd** is non-destructive, so you
	don't risk losing your source data, or getting tangled. If an action doesn't work as expected, delete it or
	update it.

Portsmouth's unique local authority code (`defined by ONS <https://www.ons.gov.uk/geography/local-authority/E06000044>`_)
is "E06000044". We need that to patch our output data into our database, and we're going to add that
as a new field. By reviewing our data we can decide on a set of actions to perform::

    >>> schema_scripts = [
            "NEW > 'la_code' < ['E06000044']",
            "RENAME > 'ba_ref' < ['Property ref no']",
            "ORDER > 'prop_ba_rates' < ['Current Rateable Value_x', 'Current Rateable Value_y', 'Current Rateable Value']",
            "ORDER > 'occupant_name' < ['Primary Liable party name_x', 'Primary Liable party name_y', 'Primary Liable party name']",
            "ORDER > 'postcode' < ['Full Property Address_x', 'Full Property Address_y', 'Full Property Address']",
            "CATEGORISE > 'occupation_state' < [+ 'Current Property Exemption Code', + 'Current Relief Type']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "CATEGORISE > 'occupation_state_reliefs' < [+ 'Current Property Exemption Code', + 'Current Relief Type']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'enterprise_zone' < 'Current Property Exemption Code'::['INDUSTRIAL']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'vacancy' < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'exempt' < 'Current Property Exemption Code'::['C', 'LOW RV', 'LAND']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
            "ORDER_NEW > 'occupation_state_date' < ['Current Prop Exemption Start Date' + 'Current Prop Exemption Start Date', 'Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date_x' + 'Account Start date_x', 'Account Start date_y' + 'Account Start date_y']",
        ]
    >>> source_data = method.get.working_data
    >>> method.add_actions(schema_scripts, source_data.uuid.hex)

Let's get in to what all of this means:

* `NEW`: is the only case where the term after the action is a `value` not a `field` reference.
* `ORDER`: is a simple first-out-last-in replacement where the value from the next field will replace 
  the current one, unless it's `nan` or empty.
* `ORDER_NEW`: is a date-comparison between the listed fields, however, you need to tie the value 
  field to a date field with the `+` modifier (in this case, they're the same, but that isn't assumed). 
  Here's it's `field_to_test_for_newnewss` + `field_with_date_reflecting_field_to_tests_newness`::

	"""ORDER_NEW > 'occupation_state_date' < ['Current Prop Exemption Start Date' + 'Current Prop Exemption Start Date', 
	'Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date_x' + 
	'Account Start date_x', 'Account Start date_y' + 'Account Start date_y']"""

* `CATEGORISE`: is the most complex operation ... there are two important modifiers: `+` and `-`.

You can think of a column of values you want to use for **categorical** data as having two broad types:

* The presence or absence of a value in a column is of interest (i.e. boolean True or False)
* The terms present in a column need to be categorised into more appropriate terms

In our tutorial data, we want to know whether a particular address is occupied or vacant. There is no
common way to present this. Some authorities are kind enough to state "true"/"false" (which is
actually the latter type of value, since they're `strings` ... make sure that's clear ;p ). Others provide a date 
when the site when vacant (so the presence of a date is an indication of vacancy). In this case, we'd modify
the field with a `-`, since the dates are not of interest for `occupation_state`, although they are
of interest for `occupation_state_date`.

In this particular case, Portsmouth have not provided any of this type of information, but instead
have indicated the category of relief that a business receives - none of which are the official
categories of relief. (*You see why people hate wrangling?*)

We need to extract those relief terms and assign them to the appropriate categories we actually want.

All of that achieved in this script::

	"CATEGORISE > 'occupation_state' < [+ 'Current Property Exemption Code', + 'Current Relief Type']",

Which is quite efficient, when you think about how long it took to explain.

Categorisation can be quite frustrating. Given that our data sources haven't published their own
schema, we don't know what the definitions are for any of the terms they use. Experience can help
you with what is most likely, but sometimes the only thing to do is go back to your source and ask.

.. note:: If your source data isn't clear, it's always best not to overfit your data and simply ignore categories that
	are not defined rather than get false positives. Be as conservative as possible in your process and **set sensible
	defaults**.

We need to assign unique values from the columns we've listed to the categorisation script. First, though, we need to
find out what terms are available to us::

    >>> df = method.transform(method.get.working_data)
    >>> list(df["Current Relief Type"].unique())
    [<NA>,
    'Retail Discount',
    'Small Business Relief England',
    'Supporting Small Business Relief',
    'Sbre Extension For 12 Months',
    'Empty Property Rate Industrial',
    'Empty Property Rate Non-Industrial',
    'Mandatory',
    'Sports Club (Registered CASC)',
    'Empty Property Rate Charitable']

And we can do the same for the other column 'Current Property Exemption Code'. Once you know what terms you want to 
assign where, the following scripts should be more obvious::

	"""ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Property Exemption Code'::['EPRN', 'EPRI', 
	'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']"""
	"""ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate
	Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']"""

Get yourself a cup of coffee. The hard part is now done.

Let's also save our method::

    >>> DIRECTORY = "/path_to/working/directory/"
    >>> FILENAME = "2020_q1_portsmouth.json"
    >>> method.save(DIRECTORY, filename=FILENAME, created_by="Gavin Chait")

Filtering is optional
^^^^^^^^^^^^^^^^^^^^^
Sometimes data are bulky. Sometimes processing data you've already imported because an updated
data source adds new rows at the bottom makes for time-consuming workflows. Filtering is not
meant to replace post-wrangling validation and processing, but to support it by importing only
the data you need.

This is an optional step. Let's set a filter to import only data released after `2010-01-01` and set the filter for our
reference column `ba_ref`::

    >>> filter_script = "FILTER_AFTER > 'occupation_state_date'::'2010-01-01'"
    >>> source_data = method.get.working_data
    >>> method.add_actions(filter_script, source_data.uuid.hex)

Transform your data
^^^^^^^^^^^^^^^^^^^
After all that, you'll be relieved (possibly) to know that there's not a lot left to do. One line::

    >>> method.build()
    >>> method.save(DIRECTORY, filename=FILENAME, created_by="Gavin Chait")

You will end up with a saved restructured Excel file, and a method `json` file. The source data are saved as Excel
for one major reason ... we often need to preserve numeric identifiers as strings. CSV is non-standard and these
identifiers are often automatically converted to numbers when opened by some programs. That can destroy identifiers
by removing leading zeros. There is no perfect way to archive data. Let me know if you have a better idea.

Method Validation
^^^^^^^^^^^^^^^^^
There's a fair amount of activity behind the scenes, mostly related to validation. Every step has
an equivalent validation step, testing the method to ensure that it will execute once your run
your transformation.

Despite all this coding and activity, you've actually made no changes to the source data. Everything you've done has 
been about documenting a process. This process is the only thing that will eventually execute and produce your output.

We can do a few things at this point::

    >>> method.validates()
	True

Since you're a sensible person, you're probably running this tutorial in a Jupyter Notebook and are interested in why it
takes a bit of time to validate::

    >>> %time assert method.validates()
	CPU times: user 53.5 s, sys: 169 ms, total: 53.6 s
	Wall time: 58.1 s

That's because validation actually runs your code. It will create a new `working_data` file and perform
all the structure and categorisation steps. None of this should make you want to lose your mind, but
- if this sort of thing is irritating - you could look into running the transformation tasks
asynchronously in the background.

Preparing a Citation
^^^^^^^^^^^^^^^^^^^^
Research-based data scientists are not always treated well in the research community. Data are hoarded by researchers, 
which also means that the people who produced that data don't get referenced or recognised.

**whyqd** is designed to support a research process and ensure citation of the incredible work done by research-based
data scientists.

A citation is a special set of fields, with options for:

* **author**: The name(s) of the author(s) (in the case of more than one author, separated by `and`),
* **title**: The title of the work,
* **url**: The URL field is used to store the URL of a web page or FTP download. It is a non-standard BibTeX field,
* **publisher**: The publisher's name,
* **institution**: The institution that was involved in the publishing, but not necessarily the publisher,
* **doi**: The doi field is used to store the digital object identifier (DOI) of a journal article, conference paper,
  book chapter or book. It is a non-standard BibTeX field. It's recommended to simply use the DOI, and not a DOI link,
* **month**: The month of publication (or, if unpublished, the month of creation). Use three-letter abbreviation,
* **year**: The year of publication (or, if unpublished, the year of creation),
* **note**: Miscellaneous extra information.

Those of you familiar with Dataverse's `universal numerical fingerprint <http://guides.dataverse.org/en/latest/developers/unf/index.html>`_
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource,
including inputs, working data, and outputs. Ours is based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_
and is included in the citation output.

Let's set up a citation for this tutorial::

    >>> citation = {
            "author": "Gavin Chait",
            "month": "feb",
            "year": 2020,
            "title": "Portsmouth City Council normalised database of commercial ratepayers",
            "url": "https://github.com/whythawk/whyqd/tree/master/tests/data"
        }
    >>> method.set_citation(citation)

You can then get your citation report::

    >>> method.get_citation()
        {'author': 'Gavin Chait',
        'title': 'Portsmouth City Council normalised database of commercial ratepayers',
        'url': AnyUrl('https://github.com/whythawk/whyqd/tree/master/tests/data', scheme='https', host='github.com', tld='com', host_type='domain', path='/whythawk/whyqd/tree/master/tests/data'),
        'month': 'feb',
        'year': 2020,
        'input_sources': [{'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls',
        'checksum': 'b180bd9fe8c3b1025f433e0b3377fb9a738523b9c33eac5d62ed83c51883e1f64a3895edf0fc9e96a85a4130df3392177dff262963338971114aa4f5d1b0a70e'},
        {'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls',
        'checksum': '98e23e4eac6782873492181d6e4f3fcf308f1bb0fc47dc582c3fdf031c020a651d9f06f6510b21405c3f63b8d576a93a27bd2f3cc5b053d8d9022c884b57d3a3'},
        {'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls',
        'checksum': '9fd3d0df6cc1e0e58ab481ca9d46b68150b3b8d0c97148a00417af16025ba066e29a35994d0e4526edb1deda4c10b703df8f0dbcc23421dd6c0c0fd1a4c6b01c'}],
        'restructured_data': {'path': 'https://github.com/whythawk/whyqd/tree/master/tests/data',
        'checksum': '25591827b9b5ad69780dc1eea6121b4ec79f10b62f21268368c7faa5ca473ef3f613c72fea723875669d0fe8aa57c9e7890f1df5b13f922fc525c82c1239eb42'}}
