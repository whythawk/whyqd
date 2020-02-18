Distribution & Citation of methods and data
===========================================

**whyqd** is designed for sharing. Simply zip up the various data files, your method JSON and upload
to your favourite data repository.

You can get a `citation` for reference (and more on how to prepare the citation at :doc:`method`)::

	method.citation

A citation is a special set of fields, with:

* **authors**: a list of author names in the format, and order, you wish to reference them
* **title**: a text field for the full study title
* **repository**: the organisation, or distributor, responsible for hosting your data (and your method file)
* **doi**: the persistent `DOI <http://www.doi.org/>`_ for your repository
* **hash**: `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_ has of output data
* **input data**: a list of input data by original source, and the source hash

Those of you familiar with Dataverse's `universal numerical fingerprint <http://guides.dataverse.org/en/latest/developers/unf/index.html>`_
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource,
including inputs, working data, and outputs. Ours is based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_
and is sufficiently universally available as to ensure you can run this as required.

Anyone with a copy of the method and input data can automatically rerun the entire method file to
produce a "new" version of the output data and so confirm more directly the validity of the data.