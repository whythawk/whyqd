from __future__ import annotations
from typing import List, TYPE_CHECKING

from uuid import uuid4

from whyqd.parsers import CoreParser
from whyqd.models import MorphActionModel

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.models import ColumnModel


class BaseMorphAction:
    """Morphs differ from Actions in that they normally act to reshape entire tables rather than manipulate columns.

    * Morph actions are not permitted to be nested, i.e. they are stand-alone ActionScripts.
    * May result in changes to column or row references that must be accounted for in other actions.

    Morphs inherit from this base class which describes the core functions and methodology for a Morph. They
    should redefine `name`, `title`, `description`, and `structure`, as well as produce a `transform` function.
    Everything else will probably remain as defined, but particularly complex Morphs should modify as required.

    `structure` can be an empty list, but a morph may be defined by these parameters:

    * `rows`: the specific rows effected by the morph, a `list` of `int`
    * `columns`: the specific columns effected by the morph, a `list` of `ColumnModel` or `FieldModel`.

    A standard script is::

        "ACTION > [columns] < [rows]"

    Where:

    * the presence and order of the arrays is set by `structure`,
    * `columns` are indicated by `>`, and
    * `rows` are indicated by `<`.
    """

    def __init__(self) -> None:
        self.core = CoreParser()
        self.name = ""
        self.title = ""
        self.description = ""
        # `structure` defines the format in which parameters for a morph are written, and validated in
        # `validate` can be any of `rows` or `columns`.
        # Where new columns are created, these will be randomly-generated and can be renamed as required.
        self.structure = []

    @property
    def settings(self) -> MorphActionModel:
        """
        Returns the dict representation of the Morph.

        Raises
        ------
        NameError if parameters don't yet exist.

        Returns
        -------
        dict
            Dict representation of a Morph.
        """
        morph_settings = {
            "name": self.name,
            "title": self.title,
            "type": "morph",
            "description": self.description,
            "structure": self.structure,
        }
        return MorphActionModel(**morph_settings)

    def transform(self, *, df: pd.DataFrame, rows: List[int], columns: List[ColumnModel]) -> pd.DataFrame:
        """
        Perform a transformation. This function must be overridden by child Morphs and describe a unique
        new method.

        .. warning:: Assumes `validates` has been run.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        **kwargs:
            Other fields which may be required in custom transforms

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        return df

    def _column_renames_to_index(self, *, df: pd.DataFrame, columns: str, hex: str) -> pd.DataFrame:
        """
        Rename randomly-generated column labels with their predictable index equivalent.

        Parameters
        ----------
        df: DataFrame
        columns: List[str]
        hex: str
            The random string used in the generator.

        Returns
        -------
        DataFrame
        """
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
        # {'from': 'too'}
        renames = {c: c.replace(hex, f"idx_{df.columns.get_loc(c)}") for c in columns}
        return df.rename(index=str, columns=renames)

    def _generate_hex(self):
        return str(uuid4().hex)[:4]
