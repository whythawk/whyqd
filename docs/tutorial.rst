Full worked tutorial
====================

**whyqd** was developed to solve a daily, grinding need in our `Sqwyre.com <https://sqwyre.com>`_
project. *Sqwyre* is an online market intelligence service helping you assess opportunities and risks 
for every commercial property in England and Wales. Every quarter, we import about 300 very messy 
spreadsheets from local authorities across the UK. These need to be restructured to conform to a 
single schema, including redefining whatever weird terms they use to describe categorical data, and 
only then can we begin the automated process of cleaning and validation. It's a mostly free
service, so you can see it in action at `Sqwyre.com <https://sqwyre.com>`_.

When we started, this was a purely manual process but, gradually, we developed what has become
**whyqd**. The process, at a high level, is as follows:

  - Create, update or import a data schema which defines the destination data structure
  - Create a new method and associate it with your schema and input data source/s
  - Assign a foreign key column and (if required) merge input data sources
  - Structure input data fields to conform to the requriements for each schema field
  - Assign categorical data identified during structuring
  - Filter and transform input data to produce a final destination data file

You are more likely to create your schema at the beginning of a project, and then spend most of your
time using that schema as the base for creating new methods for each new data source. If you're really
lucky, your data source won't change their methods from release-to-release and you can reuse your
own. In our experience that is like searching for unicorns.

The example in our worked tutorial is derived directly from our workflow at Sqwyre.com and is from a
dataset released by `Portsmouth City Council <https://www.portsmouth.gov.uk/ext/business/running-a-business/business-rates-foi-requests>`_.
The data in this tutorial are from January 2020, but follow along with the current download.

.. note:: This tutorial does assume familiarity with Python, homeopathic quantities of Pandas, and a 
	little experience with JSON.

Creating a Schema
-----------------

Review the :doc:`schema` documentation for more details. We'll start by importing **whyqd**
and defining a new schema::

	import whyqd as _w
	schema = _w.Schema()

The objective of your schema is not only to define a structure for your data, but also provide
reference and contextual information for anyone using it. In a research context, definitions are
critical to avoid ambiguity, ensure replication, and build trust.

The minimum requirement for a schema is that it have a `name`, but we're going to give it a `title`
and `description` as well, because more information is better. We're not barbarians::

	details = {
		"name": "rates_data_schema",
		"title": "UK Ratepayer data schema",
		"description": "Structural metadata target for imported messy data from the 348 local authorities in England & Wales."
	}
	schema.set_details(**details)

We can also save our schema to a specified `directory`::

	directory = "/path/to/directory"
	# you can also specify an optional filename
	# if you leave it out, the filename will default to the schema name
	filename = "2020_rates_data_schema"
	# if the file already exists, you'll need to specify `overwrite=True` otherwise you'll get
	# an error
	schema.save(directory, filename=filename, overwrite=True)

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
  are permitted and will be set to the `missing` default)
* `unique`: boolean, if `true` then all values for that input column must be unique
* `minimum`: `integer` / `number`, as appropriate defining min number of characters in a string, or 
  the min values of numbers or integers
* `maximum`: `integer` / `number`, as appropriate defining max number of characters in a string, or 
  the max values of numbers or integers
* `category`: the set of unique category terms permitted in this field
* `filter`: limit a named field by date-limited data

We'll go through most of these in the tutorial. Note that some of these are only there to support
post-wrangling (such as `minimum` or `maximum`). `required` means that a method won't be validated
if that field has no data.

We'll build a single dictionary and then iterate over the list to add each field::

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
	for field in fields:
		schema.set_field(**field)

From here on we can access any `field` by calling it by `name` and then edit it as required::

	schema.field("occupation_state_reliefs")

	{'name': 'occupation_state_reliefs',
	 'type': 'array',
	 'title': 'Occupation state reliefs',
	 'description': 'Array of the categories of reliefs / exemptions applied.'}

Let's add a list of `category` terms as a constraint for `occupation_state_reliefs`::

	categories = ["small_business", "rural", "charity", "enterprise_zone", "vacancy", "hardship", "retail", "discretionary", "exempt", "transitional", "other"]
	schema.set_field_category("occupation_state_reliefs", *categories)
	schema.field("occupation_state_reliefs")

	{'name': 'occupation_state_reliefs',
	 'type': 'array',
	 'constraints': {'category': [{'name': 'small_business'},
	   {'name': 'rural'},
	   {'name': 'charity'},
	   {'name': 'enterprise_zone'},
	   {'name': 'vacancy'},
	   {'name': 'hardship'},
	   {'name': 'retail'},
	   {'name': 'discretionary'},
	   {'name': 'exempt'},
	   {'name': 'transitional'},
	   {'name': 'other'}]},
	 'title': 'Occupation state reliefs',
	 'description': 'Array of the categories of reliefs / exemptions applied.'}

.. note:: These are the official business `rates reliefs <https://www.gov.uk/apply-for-business-rate-relief>`_
	permitted by the UK government. Unsurprisingly, only by accident do any local authorities actually 
	use these terms when awarding a relief.

We could choose to limit the `filter` field for the `occupation_state_date`, but we're not going to
bother. Review your schema, then `save` and we're ready to begin wrangling::

	schema.settings

	{'fields': [{'name': 'la_code',
	   'type': 'string',
	   'title': 'Local authority code',
	   'description': 'Standard code for local authority.'},
	  {'name': 'ba_ref',
	   'type': 'string',
	   'title': 'Billing reference',
	   'description': 'Unique code for a specific hereditament. May be multiple rows for history.'},
	  {'name': 'prop_ba_rates',
	   'type': 'number',
	   'title': 'Property billing rates',
	   'description': 'Actual rates paid by a specific ratepayer.'},
	  {'name': 'occupant_name',
	   'type': 'string',
	   'title': 'Occupier name',
	   'description': 'Name of the ratepayer.'},
	  {'name': 'postcode',
	   'type': 'string',
	   'title': 'Postcode',
	   'description': 'Full address or postcode of ratepayer.'},
	  {'name': 'occupation_state',
	   'type': 'boolean',
	   'title': 'Occupation state',
	   'description': 'Occupation status, void or occupied.'},
	  {'name': 'occupation_state_date',
	   'type': 'date',
	   'title': 'Date of occupation state',
	   'description': 'Date of the start of status in occupation_state.'},
	  {'name': 'occupation_state_reliefs',
	   'type': 'array',
	   'constraints': {'category': [{'name': 'small_business'},
		 {'name': 'rural'},
		 {'name': 'charity'},
		 {'name': 'enterprise_zone'},
		 {'name': 'vacancy'},
		 {'name': 'hardship'},
		 {'name': 'retail'},
		 {'name': 'discretionary'},
		 {'name': 'exempt'},
		 {'name': 'transitional'},
		 {'name': 'other'}]},
	   'title': 'Occupation state reliefs',
	   'description': 'Array of the categories of reliefs / exemptions applied.'}],
	 'name': 'rates_data_schema',
	 'title': 'UK Ratepayer data schema',
	 'description': 'Structural metadata target for imported messy data from the 348 local authorities in England & Wales.'}

	schema.save(directory, filename=filename, overwrite=True)

Creating a Method
-----------------

**whyqd** can import any of CSV, XLS or XLSX files, but do check that these files actually open and
are readable before proceeding. You'll be surprised at the number of supposedly open datasets
released with password-protection, fruity formatting, or which are completely corrupted.

.. warning:: The minimum required to ensure a dataset is machine-readable is that it have a header-row,
	and that there is no weird spacing or merged-fields (if you're using Excel).

In our tutorial example, the data from `Portsmouth City Council <https://www.portsmouth.gov.uk/ext/business/running-a-business/business-rates-foi-requests>`_
include three Excel (XLS) data files:

* `NDR properties January 2020`
* `NDR reliefs January 2020`
* `Empty commercial properties January 2020`

Apologies for not linking, but these are not persistent URIs. Keep that in mind in the code that
follows.

Initialise a Method and import input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the technically-minded, the :doc:`method_api` class inherits from the :doc:`schema_api` class.
This means you have all the schema functionality as well. Why have these separation of processes,
then? Because schemas are used more often than they're made, and it helps to keep the terminology
very distinct.

The only compulsory parameter needed when creating a method, is a reference to our source schema
(the one we created above). We may also offer a working directory. During the process, **whyqd** will
create a number of interim working data files, as well as your JSON method file, and your wrangled
output data. You need to tell it where to work, or it will simply drop everything into the
directory you're calling the function from.

We can also, at initialisation, provide the list of data sources::

	import whyqd as _w

	SCHEMA_SOURCE = "/full/path_to/2020_rates_data_schema.json"
	DIRECTORY = "/path_to/working/directory/"
	# Note: these links may no longer work when you follow this tutorial. Get the latest ones...
	INPUT_DATA = [
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls",
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls",
		"https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls"
	]
	method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)

These data will be copied to your working directory and renamed to a unique hashed `id`.

.. note:: **Data probity** - the abilty to audit data and methodology back to source - is critical for 
	research transparency and replication. You may end up with hundreds of similarly-named files in a 
	single directory without much information as to where they come from, or how they were created. 
	Unique ids, referenced in your method file, are a more useful way of ensuring you know what they 
	were for.

The method class provides help at each step. Access it like this::

	print(method.help())

	**whyqd** provides data wrangling simplicity, complete audit transparency, and at speed.

	To get help, type:

		>>> method.help(option)

	Where `option` can be any of:

		status
		merge
		structure
		category
		filter
		transform

	`status` will return the current method status, and your mostly likely next steps. The other options
	will return methodology, and output of that option's result (if appropriate). The `error` will
	present an error trace and attempt to guide you to fix the process problem.

	Current method status: `Ready to Merge`

Organise and Merge input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We have three input data files. These need to be consolidated into a single working data file via a
merge. **whyqd** will iteratively join files in a list, adding the 2nd to the 1st, then the 3rd, etc.

What we need to do is decide on the order, and identify a column that can be used to uniquely
cross-reference rows in each file and link them together. We start with `help`::

	# Permits horizontal scroll-bar in Jupyter Notebook
	from IPython.core.display import HTML
	display(HTML("<style>pre { white-space: pre !important; }</style>"))

	print(method.help("merge"))

	`merge` will join, in order from right to left, your input data on a common column.

	To add input data, where `input_data` is a filename, or list of filenames:

		>>> method.add_input_data(input_data)

	To remove input data, where `id` is the unique id for that input data:

		>>> method.remove_input_data(id)

	Prepare an `order_and_key` list, where each dict in the list has:

		{id: input_data id, key: column_name for merge}

	Run the merge by calling (and, optionally - if you need to overwrite an existing merge - setting
	`overwrite_working=True`):

		>>> method.merge(order_and_key, overwrite_working=True)

	To view your existing `input_data`::

		>>> method.input_data

	Data id: ab79fc32-51ce-4e9e-80cf-493af94e4177
	Original source: https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls

====  =================  =========================================================================  ==========================================  ===============  ====================  ========================
  ..  Property ref no    Full Property Address                                                      Primary Liable party name                   Analysis Code    Account Start date      Current Rateable Value
====  =================  =========================================================================  ==========================================  ===============  ====================  ========================
   0       177200066910  Unit 7b, The Pompey Centre, Dickinson Road, Southsea, Hants, PO4 8SH       City Electrical Factors  Ltd                CW               2003-11-10 00:00:00                      37000
   1       177209823010  Express By Holiday Inn, The Plaza, Gunwharf Quays, Portsmouth, PO1 3FD     Kew Green Hotels (Portsmouth Lrg1) Limited  CH               2003-11-08 00:00:00                     594000
   2       177500013310  Unit 2cd, Shawcross Industrial Estate, Ackworth Road, Portsmouth, PO3 5JP  Personal details not supplied               CG1              1994-12-25 00:00:00                      13250
====  =================  =========================================================================  ==========================================  ===============  ====================  ========================

.. code-block::

	Data id: 3b2e9893-c04c-4714-b9bb-6dd2bf274db4
	Original source: https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls

====  ===========================  =============================  =======================================================  =============================  ====================  =================================  ========================
  ..    Property Reference Number  Primary Liable party name      Full Property Address                                    Current Relief Type            Account Start date    Current Relief Award Start Date      Current Rateable Value
====  ===========================  =============================  =======================================================  =============================  ====================  =================================  ========================
   0                 177500080710  Personal details not supplied  Ground Floor, 25, Albert Road, Southsea, Hants, PO5 2SE  Retail Discount                2003-05-14 00:00:00   2019-04-01 00:00:00                                    8600
   1                 177504942310  Personal details not supplied  Ground Floor, 102, London Road, Portsmouth, PO2 0LZ      Small Business Relief England  2003-07-28 00:00:00   2005-04-01 00:00:00                                    9900
   2                 177502823510  Personal details not supplied  33, Festing Road, Southsea, Hants, PO4 0NG               Small Business Relief England  2003-07-08 00:00:00   2005-04-01 00:00:00                                    6400
====  ===========================  =============================  =======================================================  =============================  ====================  =================================  ========================

.. code-block::

	Data id: 458d7c0b-1481-487e-b120-19ccd2326d24
	Original source: https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls

====  ===========================  ================================================================  =================================  ===================================  ===============  =======================================================  ========================
  ..    Property Reference Number  Full Property Address                                             Current Property Exemption Code    Current Prop Exemption Start Date    Analysis Code    Primary Liable party name                                  Current Rateable Value
====  ===========================  ================================================================  =================================  ===================================  ===============  =======================================================  ========================
   0                 177512281010  Advertising Right, 29 Albert Road, Portsmouth, PO5 2SE            LOW RV                             2019-11-08 00:00:00                  CA1              Personal details not supplied                                                 700
   1                 177590107810  24, Ordnance Court, Ackworth Road, Portsmouth, PO3 5RZ            INDUSTRIAL                         2019-09-23 00:00:00                  IF3              Personal details not supplied                                               11000
   2                 177500058410  Unit 12, Admiral Park, Airport Service Road, Portsmouth, PO3 5RQ  EPRI                               2019-09-13 00:00:00                  CW               Legal & General Property Partners (Industrial Fund) Ltd                     26500
====  ===========================  ================================================================  =================================  ===================================  ===============  =======================================================  ========================

.. code-block::

	Current method status: `Ready to Merge`

Well, `help` shows us the first few rows of our input data, as well as their unique ids, and tells us
to prepare an `order_and_key` list, where each dict in the list has::

	{id: input_data id, key: column_name for merge}

Remember the original source file names:

* `NDR properties January 2020`
* `NDR reliefs January 2020`
* `Empty commercial properties January 2020`

You'll have to take my word for it, but that is a reasonable order, so we're good. We do need to
identify the merge columns. Each property has a unique (for a given order of "unique" ... local
government, mutter mutter) id, usually called some variation of "Property Reference". Let's create
our `order_and_key` dict and then merge (and your reference ids will be different)::

	oak = [
		{
			"id": "ab79fc32-51ce-4e9e-80cf-493af94e4177",
			"key": "Property ref no"
		},
		{
			"id": "3b2e9893-c04c-4714-b9bb-6dd2bf274db4",
			"key": "Property Reference Number"
		},
		{
			"id": "458d7c0b-1481-487e-b120-19ccd2326d24",
			"key": "Property Reference Number"
		}
	]
	method.merge(order_and_key=oak)

	UserWarning: '3b2e9893-c04c-4714-b9bb-6dd2bf274db4.xls' contains non-unique rows in column `Property Reference Number`
	UserWarning: '458d7c0b-1481-487e-b120-19ccd2326d24.xls' contains non-unique rows in column `Property Reference Number`

OK, what does that `warning` mean?

This is where we need a brief digression into the use of `data as a science <https://github.com/whythawk/data-as-a-science/>`_
(*and, why yes, we are working on exactly such a course, why do you ask?*).

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
clear on what you're doing at each step rather than getting all recursive in your methods::

	print(method.help("status"))

	Current method status: `Ready to Structure`

Create a wrangling Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Critically, **whyqd** is for *repeatable* processing. Next quarter, Portsmouth will update their data
and we want to import it again. However, it probably won't be in the same format as this quarter
since a human being prepared and uploaded these data. That person doesn't know about your use-case
and probably doesn't care (at least they haven't accused you of `promoting terrorism <http://informationrights.decisions.tribunals.gov.uk/DBFiles/Decision/i2557/Westminster%20City%20Council%20EA-2018-0033%20(04.12.19).pdf>`_
with these data). Maybe they change some column names. The URI will definitely be different, and maybe
so will the file order. These are simple changes and all that's required is a minor adjustment to the
method to run this process again.

Let's start with `help`::

	print(method.help("structure"))

	`structure` is the core of the wrangling process and is the process where you define the actions
	which must be performed to restructure your working data.

	Create a list of methods of the form:

		{
			"schema_field1": ["action", "column_name1", ["action", "column_name2"]],
			"schema_field2": ["action", "column_name1", "modifier", ["action", "column_name2"]],
		}

	The format for defining a `structure` is as follows::

		[action, column_name, [action, column_name]]

	e.g.::

		["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

	This permits the creation of quite expressive wrangling structures from simple building
	blocks.

	The schema for this method consists of the following terms:

	['la_code', 'ba_ref', 'prop_ba_rates', 'occupant_name', 'postcode', 'occupation_state',
	'occupation_state_date', 'occupation_state_reliefs']

	The actions:

	['NEW', 'ORDER', 'ORDER_NEW', 'ORDER_OLD', 'CALCULATE', 'CATEGORISE', 'JOIN']

	The columns from your working data:

	['Property ref no', 'Full Property Address_x', 'Primary Liable party name_x', 'Analysis Code_x',
	'Account Start date_x', 'Current Rateable Value_x', 'Property Reference Number_x',
	'Primary Liable party name_y', 'Full Property Address_y', 'Current Relief Type',
	'Account Start date_y', 'Current Relief Award Start Date', 'Current Rateable Value_y',
	'Property Reference Number_y', 'Full Property Address', 'Current Property Exemption Code',
	'Current Prop Exemption Start Date', 'Analysis Code_y', 'Primary Liable party name',
	'Current Rateable Value']

	Data id: a9b99aaf-438d-44cd-bf38-4849edac0c66
	Original source: method.input_data

====  ======================  ======================  =================  =================  ===================================  =================================  ========================  ==========================  ==========================  =================================  =====================  =======================  =========================================================================  =========================================================================  ===========================  ==========================================  =============================  =============================  =============================  =================
  ..  Account Start date_x    Account Start date_y    Analysis Code_x      Analysis Code_y    Current Prop Exemption Start Date    Current Property Exemption Code    Current Rateable Value    Current Rateable Value_x    Current Rateable Value_y  Current Relief Award Start Date    Current Relief Type      Full Property Address  Full Property Address_x                                                    Full Property Address_y                                                      Primary Liable party name  Primary Liable party name_x                 Primary Liable party name_y      Property Reference Number_x    Property Reference Number_y    Property ref no
====  ======================  ======================  =================  =================  ===================================  =================================  ========================  ==========================  ==========================  =================================  =====================  =======================  =========================================================================  =========================================================================  ===========================  ==========================================  =============================  =============================  =============================  =================
   0  2003-11-10 00:00:00     NaT                     CW                               nan                                  nan                                nan                       nan                       37000                         nan  NaT                                nan                                        nan  Unit 7b, The Pompey Centre, Dickinson Road, Southsea, Hants, PO4 8SH       nan                                                                                                nan  City Electrical Factors  Ltd                nan                                              nan                                    nan       177200066910
   1  2003-11-08 00:00:00     NaT                     CH                               nan                                  nan                                nan                       nan                      594000                         nan  NaT                                nan                                        nan  Express By Holiday Inn, The Plaza, Gunwharf Quays, Portsmouth, PO1 3FD     nan                                                                                                nan  Kew Green Hotels (Portsmouth Lrg1) Limited  nan                                              nan                                    nan       177209823010
   2  1994-12-25 00:00:00     1994-12-25 00:00:00     CG1                              nan                                  nan                                nan                       nan                       13250                       13250  2019-04-01 00:00:00                Retail Discount                            nan  Unit 2cd, Shawcross Industrial Estate, Ackworth Road, Portsmouth, PO3 5JP  Unit 2cd, Shawcross Industrial Estate, Ackworth Road, Portsmouth, PO3 5JP                          nan  Personal details not supplied               Personal details not supplied                      1.775e+11                            nan       177500013310
====  ======================  ======================  =================  =================  ===================================  =================================  ========================  ==========================  ==========================  =================================  =====================  =======================  =========================================================================  =========================================================================  ===========================  ==========================================  =============================  =============================  =============================  =================

.. code-block::

	Current method status: `Ready to Structure`

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

Portsmouth's unique local authority code (`defined by ONS <https://www.ons.gov.uk/geography/local-authority/E06000044>`_)
is "E06000044". We need that to patch our output data into our database, and we're going to add that
as a new field. The rest of the data can be derived from our working data in the `help` summary::

	structure = {
		"la_code": ["NEW", "E06000044"],
		"ba_ref": ["ORDER", "Property Reference Number_y", "Property Reference Number_x", "Property ref no"],
		"prop_ba_rates": ["ORDER", "Current Rateable Value_x", "Current Rateable Value_y", "Current Rateable Value"],
		"occupant_name": ["ORDER", "Primary Liable party name_x", "Primary Liable party name_y", "Primary Liable party name"],
		"postcode": ["ORDER", "Full Property Address_x", "Full Property Address_y", "Full Property Address"],
		"occupation_state": ["CATEGORISE",
			"+", "Current Property Exemption Code",
			"+", "Current Relief Type"],
		"occupation_state_date": ["ORDER_NEW",
			"Current Prop Exemption Start Date", "+", "Current Prop Exemption Start Date",
			"Current Relief Award Start Date", "+", "Current Relief Award Start Date",
			"Account Start date_x", "+", "Account Start date_x",
			"Account Start date_y", "+", "Account Start date_y"],
		"occupation_state_reliefs": ["CATEGORISE",
			"+", "Current Property Exemption Code",
			"+", "Current Relief Type"]
	}
	method.set_structure(**structure)

Let's get in to what all of this means:

* `NEW`: is the only case where the term after the action is a `value` not a `field` reference.
* `ORDER`: is a simple first-out-last-in replacement where the value from the next field will replace 
  the current one, unless it's `nan` or empty.
* `ORDER_NEW`: is a date-comparison between the listed fields, however, you need to tie the value 
  field to a date field with the `+` modifier (in this case, they're the same, but that isn't assumed). 
  Here's it's `field_to_test_for_newnewss` + `field_with_date_reflecting_field_to_tests_newness`::

		"occupation_state_date": ["ORDER_NEW",
			"Current Prop Exemption Start Date", "+", "Current Prop Exemption Start Date",
			"Current Relief Award Start Date", "+", "Current Relief Award Start Date",
			"Account Start date_x", "+", "Account Start date_x",
			"Account Start date_y", "+", "Account Start date_y"]

* `CATEGORISE`: is the most complex operation (and has another step) ... there are two important 
  modifiers: `+` and `-`.

You can think of a column of values you want to use for **categorical** data as having two broad types:

* The presence or absence of a value in a column is of interest (i.e. boolean True or False)
* The terms present in a column need to be categorised into more appropriate terms

In our tutorial data, we want to know whether a particular address is occupied or vacant. There is no
common way to present this. Some authorities are kind enough to state "true"/"false" (which is
actually the latter type of value ... make sure that's clear ;p ). Others provide a date when the
site when vacant (so the presence of a date is an indication of vacancy). In this case, we'd modify
the field with a `-`, since the dates are not of interest for `occupation_state`, although they are
of interest for `occupation_state_date`.

In this particular case, Portsmouth have not provided any of this type of information, but instead
have indicated the category of relief that a business receives - none of which are the official
categories of relief. (*You see why people hate wrangling?*)

We need to extract those relief terms and assign them to the appropriate categories we actually want.

All of that achieved in this phrase::

		"occupation_state_reliefs": ["CATEGORISE",
			"+", "Current Property Exemption Code",
			"+", "Current Relief Type"]

Which is quite efficient, when you think about how long it took to explain.

This brings us to the end of structuring::

	print(method.help("status"))

	Current method status: `Ready to Categorise`

Assigning Category terms to fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Categorisation can be quite frustrating. Given that our data sources haven't published their own
schema, we don't know what the definitions are for any of the terms they use. Experience can help
you with what is most likely, but sometimes the only thing to do is go back to your source and ask.

If they won't tell you, it's always best not to overfit your data and simply ignore categories that
are not defined rather than get false positives. Be as conservative as possible in your process.

Let's start with `help`::

	print(method.help("category"))

	Provide a list of categories of the form::

		{
			"schema_field1": {
				"category_1": ["term1", "term2", "term3"],
				"category_2": ["term4", "term5", "term6"]
			}
		}

	The format for defining a `category` term as follows::

		`term_name::column_name`

	Get a list of available terms, and the categories for assignment, by calling::

		>>> method.category(field_name)

	Once your data are prepared as above::

		>>> method.set_category(**category)

	Field names requiring categorisation are: ['occupation_state', 'occupation_state_reliefs']

	Current method status: `Ready to Categorise`

Hmm, **whyqd** making us do some work here remembering which fields we wanted to categories. Well,
ok then::

	method.category("occupation_state")

	{'categories': ['true', 'false'],
	 'assigned': {},
	 'unassigned': ['Retail Discount::Current Relief Type',
	  'Small Business Relief England::Current Relief Type',
	  'Supporting Small Business Relief::Current Relief Type',
	  'Sbre Extension For 12 Months::Current Relief Type',
	  'Empty Property Rate Industrial::Current Relief Type',
	  'Empty Property Rate Non-Industrial::Current Relief Type',
	  'Mandatory::Current Relief Type',
	  'Sports Club (Registered CASC)::Current Relief Type',
	  'Empty Property Rate Charitable::Current Relief Type',
	  'EPRI::Current Property Exemption Code',
	  'ANCIENT::Current Property Exemption Code',
	  'LISTED::Current Property Exemption Code',
	  'EPRN::Current Property Exemption Code',
	  'VOID::Current Property Exemption Code',
	  'LIQUIDATE::Current Property Exemption Code',
	  'LAND::Current Property Exemption Code',
	  'LOW RV::Current Property Exemption Code',
	  'INDUSTRIAL::Current Property Exemption Code',
	  'ADMIN::Current Property Exemption Code',
	  'LA ACTION::Current Property Exemption Code',
	  'C::Current Property Exemption Code',
	  'DECEASED::Current Property Exemption Code',
	  'PROHIBITED::Current Property Exemption Code',
	  'BANKRUPT::Current Property Exemption Code',
	  'EPCH::Current Property Exemption Code']}

For `occupation_state` we have two categories "true" and "false" (not, text, not boolean terms), and
a long list of `unassigned` terms we can use. Notice the terminology `term_name::column_name`. There
may be multiple columns with multiple identical terms. We need to keep track ... Let's create our
`category` dict for `occupation_state`::

	category = {
		"occupation_state": {
			"false": [
				'EPRN::Current Property Exemption Code',
				'EPRI::Current Property Exemption Code',
				'VOID::Current Property Exemption Code',
				'Empty Property Rate Non-Industrial::Current Relief Type',
				'Empty Property Rate Industrial::Current Relief Type',
				'EPCH::Current Property Exemption Code',
				'LIQUIDATE::Current Property Exemption Code',
				'DECEASED::Current Property Exemption Code',
				'PROHIBITED::Current Property Exemption Code',
				'BANKRUPT::Current Property Exemption Code',
				'Empty Property Rate Charitable::Current Relief Type'
			]
		}
	}
	method.set_category(**category)

We didn't need to set anything for "true" because we didn't have anything. We could have set the
categories for both `occupation_state_reliefs` and `occupation_state` at the same time (in a single
dict), but for this tutorial it'll help to keep them distinct::

	method.category("occupation_state_reliefs")

	{'categories': ['small_business',
	  'rural',
	  'charity',
	  'enterprise_zone',
	  'vacancy',
	  'hardship',
	  'retail',
	  'discretionary',
	  'exempt',
	  'transitional',
	  'other'],
	 'assigned': {},
	 'unassigned': ['Retail Discount::Current Relief Type',
	  'Small Business Relief England::Current Relief Type',
	  'Supporting Small Business Relief::Current Relief Type',
	  'Sbre Extension For 12 Months::Current Relief Type',
	  'Empty Property Rate Industrial::Current Relief Type',
	  'Empty Property Rate Non-Industrial::Current Relief Type',
	  'Mandatory::Current Relief Type',
	  'Sports Club (Registered CASC)::Current Relief Type',
	  'Empty Property Rate Charitable::Current Relief Type',
	  'EPRI::Current Property Exemption Code',
	  'ANCIENT::Current Property Exemption Code',
	  'LISTED::Current Property Exemption Code',
	  'EPRN::Current Property Exemption Code',
	  'VOID::Current Property Exemption Code',
	  'LIQUIDATE::Current Property Exemption Code',
	  'LAND::Current Property Exemption Code',
	  'LOW RV::Current Property Exemption Code',
	  'INDUSTRIAL::Current Property Exemption Code',
	  'ADMIN::Current Property Exemption Code',
	  'LA ACTION::Current Property Exemption Code',
	  'C::Current Property Exemption Code',
	  'DECEASED::Current Property Exemption Code',
	  'PROHIBITED::Current Property Exemption Code',
	  'BANKRUPT::Current Property Exemption Code',
	  'EPCH::Current Property Exemption Code']}

Here it's a little more complex to assign everything, but still reasonably clear::

	category = {
		"occupation_state_reliefs": {
			"small_business": [
				'Small Business Relief England::Current Relief Type',
				'Sbre Extension For 12 Months::Current Relief Type',
				'Supporting Small Business Relief::Current Relief Type'
			],
			"enterprise_zone": ['INDUSTRIAL::Current Property Exemption Code'],
			"vacancy": [
				'EPRN::Current Property Exemption Code',
				'EPRI::Current Property Exemption Code',
				'VOID::Current Property Exemption Code',
				'Empty Property Rate Non-Industrial::Current Relief Type',
				'Empty Property Rate Industrial::Current Relief Type',
				'EPCH::Current Property Exemption Code',
				'LIQUIDATE::Current Property Exemption Code',
				'DECEASED::Current Property Exemption Code',
				'PROHIBITED::Current Property Exemption Code',
				'BANKRUPT::Current Property Exemption Code',
				'Empty Property Rate Charitable::Current Relief Type'
			],
			"retail": ['Retail Discount::Current Relief Type'],
			"exempt": [
				'C::Current Property Exemption Code',
				'LOW RV::Current Property Exemption Code',
				'LAND::Current Property Exemption Code'
			],
			"other": [
				'Sports Club (Registered CASC)::Current Relief Type',
				'Mandatory::Current Relief Type'
			]
		}
	}
	method.set_category(**category)

Get yourself a cup of coffee. The hard part is now done::

	print(method.help("status"))

	Current method status: `Ready to Transform`

Let's also save our method::

	DIRECTORY = "/path_to/working/directory/"
	FILENAME = "2020_q1_portsmouth.json"
	method.save(DIRECTORY, filename=FILENAME, overwrite=True)

Filtering is optional
^^^^^^^^^^^^^^^^^^^^^

Sometimes data are bulky. Sometimes processing data you've already imported because an updated
data source adds new rows at the bottom makes for time-consuming workflows. Filtering is not
meant to replace post-wrangling validation and processing, but to support it by importing only
the data you need.

This is an optional step, and we start with `help`::

	print(method.help("filter"))

	Set date filters on any date-type fields. **whyqd** offers only rudimentary post-
	wrangling functionality. Filters are there to, for example, facilitate importing data
	outside the bounds of a previous import.

	This is also an optional step. By default, if no filters are present, the transformed output
	will include `ALL` data.

	Parameters
	----------
	field_name: str
		Name of field on which filters to be set
	filter_name: str
		Name of filter type from the list of valid filter names
	filter_date: str (optional)
		A date in the format specified by the field type
	foreign_field: str (optional)
		Name of field to which filter will be applied. Defaults to `field_name`

	There are four filter_names:

		ALL: default, import all data
		LATEST: only the latest date
		BEFORE: before a specified date
		AFTER: after a specified date

	BEFORE and AFTER take an optional `foreign_field` term for filtering on that column. e.g.

		>>> method.set_filter("occupation_state_date", "AFTER", "2019-09-01", "ba_ref")

	Filters references in column `ba_ref` by dates in column `occupation_state_date` after `2019-09-01`.

	Field names which can be filtered are: ['occupation_state_date']

Let's set a filter to import only data released after `2010-01-01` and set the filter for our
reference column `ba_ref`::

	method.set_filter("occupation_state_date", "AFTER", "2010-01-01", "ba_ref")
	method.save(DIRECTORY, filename=FILENAME, overwrite=True)

Method Validation
^^^^^^^^^^^^^^^^^

There's a fair amount of activity behind the scenes, mostly related to validation. Every step has
an equivalent validation step, testing the method to ensure that it will execute once your run
your transformation.

At this state, except for creating a `working_data` file, you've actually made no changes to the
underlying data. Everything you've done has been about documenting a process. This process is the
only thing that will eventually execute and produce your output.

We can do a few things at this point::

	method.validates

	UserWarning: '3b2e9893-c04c-4714-b9bb-6dd2bf274db4.xls' contains non-unique rows in column `Property Reference Number`
	UserWarning: '458d7c0b-1481-487e-b120-19ccd2326d24.xls' contains non-unique rows in column `Property Reference Number`

	True

Aside from the warning, which we already know about, your method validates. Since you're a sensible
person, you're probably running this tutorial in a Jupyter Notebook and are interested in why it
takes a bit of time to validate::

	%time method.validates

	CPU times: user 7.27 s, sys: 172 ms, total: 7.44 s
	Wall time: 7.5 s

	True

That's because validation actually runs your code. It will create a new working_data file and perform
all the structure and categorisation steps. None of this should make you want to lose your mind, but
- if this sort of thing is irritating - you could look into running the transformation tasks
asynchronously in the background.

If you want to look at your method, do the following (I'm not reproducing the output here)::

	method.settings

OK, everything validates, and we're ready to transform...

Transform your data
^^^^^^^^^^^^^^^^^^^

After all that, you'll be relieved (possibly) to know that there's not a lot left to do. One line::

	method.transform()
	method.save(DIRECTORY, filename=FILENAME, overwrite=True)

With one little permutation ... if you've ever created a transform before, you'll need to deliberately
tell the function to overwrite your original::

	method.transform(overwrite_output=True)

And, then, because you're appropriately paranoid::

	method.validate_transform

	True

Preparing a Citation
^^^^^^^^^^^^^^^^^^^^

Data scientists (with the emphasis on the `science` part) are not always treated well in the research
community. Data are hoarded by researchers, which also means that the people who produced that data
don't get referenced or recognised.

**whyqd** is designed for sharing. To produce a full citation for your dataset, there's one last
requirement. Add information you wish to be cited to a `constructor` field in the `method`.

The `constructor` field is there to store any metadata you wish to add. Whether it be `Dublin Core <https://dublincore.org/>`_
or `SDMX <https://sdmx.org/>`_, add that metadata by creating a dictionary and placing it in the
`constructor`.

A citation is a special set of fields, with the minimum of:

* **authors**: a list of author names in the format, and order, you wish to reference them
* **date**: publication date (uses transformation date, if not provided)
* **title**: a text field for the full study title
* **repository**: the organisation, or distributor, responsible for hosting your data (and your method file)
* **doi**: the persistent `DOI <http://www.doi.org/>`_ for your repository

Those of you familiar with Dataverse's `universal numerical fingerprint <http://guides.dataverse.org/en/latest/developers/unf/index.html>`_
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource,
including inputs, working data, and outputs. Ours is based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_
and is sufficiently universally available as to ensure you can run this as required.

Let's create a citation for this tutorial::

	citation = {
		"authors": ["Gavin Chait"],
		"title": "Portsmouth City Council normalised database of commercial ratepayers",
		"repository": "Github.com"
	}
	method.set_constructors({"citation": citation})
	method.save(DIRECTORY, filename=FILENAME, overwrite=True)

You can then get your citation report::

	method.citation

	Gavin Chait, 2020-02-18, Portsmouth City Council normalised database of commercial ratepayers,
	Github.com, 1367d4f02c99030f6645389141b85a93d54c226b435fb1b5a6cbccd7f703687e442a011f62c1381793a2d3fbf13cc52c176e0c5c573008991134658759eef948,
	[input sources:
	https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls,
	476089d8f37581613344873068d6e94f8cd63a1a64b421edf374a2b341bc7563aff03b86db4d3fec8ca90ce150ba1e531e3ff0d374f932d13fc103fd709e01bd;
	https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls,
	892ec5b6e9b1f68e0b371bbaed8d93095d57f2b656753af2b279aee17b5854c5e9d731b2795aac285d7f7d9f5991311bc8fae0cfe5446a47163f30f0314cac06;
	https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls,
	a41b4eb629c249fd59e6816d10d113bf2b9594c7dd7f9a61a82333a8a41bf07e59f9104eb3c1dc4269607de5a4a12eaf3215d0afc7545fdb1dfe7fe1bf5e0d29]
