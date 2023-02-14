"""
Actions
-------

Definitions and validation for actions anchoring structures in methods. Describes how an Action performs its roll. 
New transforms inherit from the core.BaseSchemaAction class and are automatically available as a plugin.

Key functions are:

  - Define action settings
  - Specify any modifiers
  - Validate action structure
  - Perform action dataframe transformation

The structure of an action (JSON or dict) saved in a method (and presented to the `action.transform` funtion)::

    [
        {
            "description": "",
            "name": "ACTION",
            "structure": [
                "field"
            ],
            "title": "Title",
            "type": "action"
        },
        {
            "name": "field",
            "type": "type"
        }
    ]

Where the first term in the list if the action (as would appear in `action.settings`) and the subsequent fields
must conform to the structure defined in the action's structure, but with a format that can be accessed in the 
`action.transform` function. Normally this would be a `name` and `type`, but any created value would have a `value`
instead of a `name`.
"""
import pkgutil
from pathlib import Path

__action_path__ = str(Path(__file__).resolve().parent)

actions = {
    name.upper(): finder.find_module(name).load_module().Action
    for finder, name, _ispkg in pkgutil.iter_modules([__action_path__])
}
default_actions = [a for a in [actn().settings for actn in actions.values()]]
