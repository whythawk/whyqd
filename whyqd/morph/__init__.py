"""
Morphs
------

Definitions and validation for morphs transforming tabular data. Describes how a Morph performs its roll. 
New transforms inherit from the core.BaseMorph class and are automatically available as a plugin.

Key functions are:

  - Define morph settings
  - Specify any transformation parameters (`structure`)
  - Validate morph parameters
  - Perform dataframe transformation

The structure of a morph (JSON or dict) saved in a method (and presented to the `morph.transform` funtion)::

    [
        {
            "name": "xxxxx",
            "parameters": {
                "rows": [1,2,3],
                "columns": ["column1"]
            }
        }
    ]

Where the first term in the list of the morphs (as would appear in `morph.settings`) and the subsequent fields
must conform to the structure defined in the morph's structure, but with a format that can be accessed in the 
`morph.transform` function. Normally this would be a `name` and `parameters`.
"""
import pkgutil
from whyqd.core import common as _c
__morph_path__ = str(_c.get_path()) + "/morph"

morphs = {
    name.upper(): finder.find_module(name).load_module().Morph
    for finder, name, ispkg
    in pkgutil.iter_modules([__morph_path__])
}

default_morphs = {
    "fields": [
        mrph().settings for mrph in morphs.values()
    ]
}