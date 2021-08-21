from __future__ import annotations
from typing import Optional, Union, List, Tuple, Dict, TYPE_CHECKING
from uuid import UUID
import pandas as pd

from . import ActionScript, ParserScript, CategoryScript, MorphScript, FilterScript
from ..models import SchemaActionModel, MorphActionModel, CategoryActionModel, FilterActionModel, ColumnModel

if TYPE_CHECKING:
    # Adam Johnson, you're a hero. This took 6 hours to solve.
    # https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
    from ..models import DataSourceModel, ActionScriptModel, MethodModel
    from ..schema import Schema


class MethodScript:
    """Parsing functions for methods."""

    def __init__(self, schema: Schema):
        self.schema = schema
        self.parser = ParserScript()

    ###################################################################################################
    ### PARSE DATA SOURCES
    ###################################################################################################

    def get_source_data(self, method: MethodModel, uid: UUID, sheet_name: Optional[str] = None) -> DataSourceModel:
        """Return a unique data source.

        Parameters
        ----------
        method: MethodModel
            A method, including references to input and interm data sources.
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if data source does not exist.

        Returns
        -------
        DataSourceModel
        """
        source = None
        if method.working_data and method.working_data.uuid == UUID(uid):
            source = method.working_data
        elif method.input_data:
            source = self.get_input_data(method.input_data, uid, sheet_name)
        if not source:
            raise ValueError(f"Data source ({' '.join([uid, sheet_name])}) does not exist")
        return source

    def get_input_data(
        self, input_data: List[DataSourceModel], uid: UUID, sheet_name: Optional[str] = None
    ) -> DataSourceModel:
        """Return a unique input data source, or raise an error if it doesn't exist.

        Parameters
        ----------
        input_data: List[DataSourceModel]
            A list of input data conforming to the DataSourceModel.
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        # https://stackoverflow.com/a/31988734/295606
        if sheet_name:
            ds = next(
                (d for d in input_data if d.uuid == UUID(uid) and d.sheet_name == sheet_name),
                None,
            )
        else:
            ds = next((d for d in input_data if d.uuid == UUID(uid)), None)
            if ds.sheet_name:
                raise ValueError(f"Data source ({ds.path}) has multiple sheets. Specify which one to modify.")
        return ds

    def reorder_models(
        self,
        model_list: Union[List[ActionScriptModel], List[DataSourceModel]],
        order: List[Union[UUID, Tuple[UUID, str]]],
    ) -> Union[List[ActionScriptModel], List[DataSourceModel]]:
        """Return a reordered list of models.

        Parameters
        ----------
        model_list: list of ActionScriptModel, or DataSourceModel
        order: list of UUID or tuples of UUID, str

        Raises
        ------
        ValueError if the list of uuid4s doesn't conform to that in the list of models.
        """
        if set([(m.uuid, m.sheet_name) if m.sheet_name else m.uuid for m in model_list]).difference(
            set([(UUID(o[0]), o[1]) if isinstance(o, tuple) else UUID(o) for o in order])
        ):
            raise ValueError("List of reordered model ids isn't the same as that in the provided list of Models.")
        return sorted(
            model_list,
            key=lambda item: order.index((item.uuid.hex, item.sheet_name))
            if item.sheet_name
            else order.index(item.uuid.hex),
        )

    ###################################################################################################
    ### PARSE ACTION SCRIPTS
    ###################################################################################################

    def parse_action_script(
        self, source_data: DataSourceModel, script: ActionScriptModel
    ) -> Dict[str, Union[list, str]]:
        """Return a parsed script ready to wrangle a data source.

        Parameters
        ----------
        source_data: DataSourceModel
        script: ActionScriptModel

        Returns
        -------
        dict
            Dict will have keys for 'action', 'destination' (if root ACTION), and 'source'. Source lists may be nested
            depending on the script.
        """
        scrpt = script.script  # reduce to text
        first_action = self.parser.get_anchor_action(scrpt)
        # Test for the special case of a source data merge
        # Since this is a *whole other thing*(TM) it must be handled separately
        if first_action.name == "MERGE":
            raise ValueError(
                "'MERGE' action must be parsed differently. Call `method.merge_input_data(script)` instead."
            )
        # Test for each of SchemaActionModel, MorphActionModel, CategoryActionModel, FilterActionModel
        if isinstance(first_action, SchemaActionModel):
            return ActionScript(source_data.columns, self.schema).parse(scrpt)
        if isinstance(first_action, MorphActionModel):
            return MorphScript(source_data, self.schema).parse(scrpt)
        if isinstance(first_action, CategoryActionModel):
            return CategoryScript(source_data, self.schema).parse(scrpt)
        if isinstance(first_action, FilterActionModel):
            return FilterScript(source_data, self.schema).parse(scrpt)
        # First action unknown
        raise ValueError(f"Script cannot be parsed ({scrpt}).")

    def remove_action(self, action_list: List[ActionScriptModel], uid: UUID) -> List[ActionScriptModel]:
        """Remove an action from a list of ActionModels, defined by its unique UUID.

        Parameters
        ----------
        action_list: list of ActionScriptModel
        uid: str
            Unique uuid4 for one of the actions."""
        return [a for a in action_list if a.uuid != UUID(uid)]

    def update_actions(
        self, action_list: List[ActionScriptModel], uid: UUID, new_action: ActionScriptModel
    ) -> List[ActionScriptModel]:
        """Return a reordered list of models.

        Parameters
        ----------
        action_list: list of ActionScriptModel
        uid: str
            Unique uuid4 for one of the actions.
        action: ActionScriptModel
            An updated ActionScriptModel to replace that defined at uid.

        Raises
        ------
        ValueError if the list of uuid isn't in the list of action models.
        """
        # https://stackoverflow.com/a/4391722/295606
        old_action_index = next((index for (index, a) in enumerate(action_list) if a.uuid == UUID(uid)), None)
        if not old_action_index:
            raise ValueError(f"Action ({uid}) is not a member of the list of actions.")
        return [a if a.uuid != UUID(uid) else new_action for a in action_list]

    ###################################################################################################
    ### IMPLEMENT VALIDATED ACTIONS
    ###################################################################################################

    def transform_df_from_source(self, df: pd.DataFrame, source_data: DataSourceModel, **params) -> pd.DataFrame:
        """Parse a script and implement it.

        Requires testing for the specific class of ACTION.

        Parameters
        ----------
        df: DataFrame
            Source data for transformation.
        source_data: DataSourceModel
        params: dict of kwargs
            Parsed action script response for Morph and Schema ACTIONS

        Returns
        -------
        DataFrame
        """
        # Test for each of SchemaActionModel, MorphActionModel, FilterActionModel
        if isinstance(params["action"], SchemaActionModel):
            return ActionScript(source_data.columns, self.schema).transform(df, **params)
        if isinstance(params["action"], MorphActionModel):
            return MorphScript(source_data, self.schema, df=df).transform(**params)
        if isinstance(params["action"], FilterActionModel):
            return FilterScript(source_data, self.schema).transform(df, **params)

    ###################################################################################################
    ### PARSE MERGE ACTION
    ###################################################################################################

    def parse_merge(self, script: ActionScriptModel, input_data: List[DataSourceModel]) -> List[DataSourceModel]:
        """Parser for the MERGE script. Produces required terms and validates against requirements.

        Script is of the form::

            "MERGE < ['key_column'::'source_hex'::'sheet_name', ...]"

        .. note:: There can only be *one* interim data source, and only *one* `MERGE` script, which must also be
            *first* in the list of `ACTIONs` for that data source.

        Parameters
        ----------
        script: ActionScriptModel
            A `MERGE` action script.
        input_data: List[DataSourceModel]
            A list of input data conforming to the DataSourceModel.

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        list of DataSourceModel
            Parsed list of updated input source data DataSourceModels.
        """
        action_model = self.parser.get_anchor_action(script.script)
        if action_model.name != "MERGE":
            raise ValueError(f"Invalid action ({action_model.name}) for this parser.")
        # Validate the MERGE script and get the required input data sources
        MERGE = self.parser.get_action_class(action_model)
        merge_terms = MERGE().parse(script.script)
        merge_list = []
        # Check if the source data exist
        for key, uid, sheet_name in merge_terms:
            data = self.get_input_data(input_data, uid, sheet_name)
            if not data:
                raise ValueError(f"MERGE data source ({(uid, sheet_name)}) is not a valid reference.")
            data.key = ColumnModel(**{"name": key})
            merge_list.append(data)
        if len(merge_list) < 2:
            raise ValueError("MERGE script performs a merge on less than two data sources. This is unnecessary.")
        return merge_list
