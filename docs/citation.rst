Distribution & Citation of methods and data
===========================================

**whyqd** is designed to support a research process and ensure citation of the incredible work done by research-based
data scientists. Simply zip up the various data files, your method JSON and upload to your favourite data repository.

You can get a `citation` for reference (and more on how to prepare the citation at :doc:`method`)::

    >>> method.get_citation()

A citation is a special set of fields, with:

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

Anyone with a copy of your method and input data can automatically rerun your entire method file to produce a "new" 
version of the output data and so confirm more directly the validity of your restructured research data.




