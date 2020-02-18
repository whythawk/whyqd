Roadmap
=======

.. note:: **whyqd** has the single objective of transforming messy input data into a single standardised schema for further validation and analyis in other software. Anything that goes further than that is out of scope.

That still leaves a fair amount to do, including improving the documentation and tests:

* Zip data files, method, and produce citation report as a single step to aid distribution
* Validate a zipped output file and produce a validation report
* Setting the `missing_data` function doesn't do anything at the moment
* Potentially refactor `transform.py` to make it more expressive and extensible?
* Additional transformations / actions:

  * Pivots: some data are horizontal instead of vertical, e.g.

   =======  ====  ====  ====
   details  2010  2015  2020
   =======  ====  ====  ====
   Fish      200   350   500
   Cats      120    80    40
   =======  ====  ====  ====

   We need an `action` to convert that to, e.g.:

   =======  ====  =====
   details  year  value
   =======  ====  =====
   Fish     2010    200
   Fish     2015    350
   Fish     2020    500
   Cats     2010    120
   Cats     2015     80
   Cats     2020     40
   =======  ====  =====

And, then, what would you like to see?