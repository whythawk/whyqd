from __future__ import annotations
from typing import Optional, Dict, List, Union, Type, TYPE_CHECKING
from datetime import date, datetime
import pandas as pd
import numpy as np
import re
import locale

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
    # Readthedocs has a problem, but difficult to replicate
    locale.setlocale(locale.LC_ALL, "")

from . import CoreScript
from ..models import ColumnModel
from ..types import MimeType

if TYPE_CHECKING:
    from ..schema import Schema


class WranglingScript:
    """Get, review and restructure tabular data."""

    def __init__(self):
        self.check_source = CoreScript().check_source
        self.DATE_FORMATS = {
            "date": {"fmt": ["%Y-%m-%d"], "txt": ["YYYY-MM-DD"]},
            "datetime": {
                "fmt": ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S %Z%z"],
                "txt": ["YYYY-MM-DD hh:mm:ss", "YYYY-MM-DD hh:mm:ss UTC+0000"],
            },
            "year": {"fmt": ["%Y"], "txt": ["YYYY"]},
        }

    def get_dataframe(
        self,
        source: str,
        preserve: Union[str, List[str]] = None,
        filetype: MimeType = MimeType.CSV,
        names: Optional[List[str]] = None,
        nrows: Optional[int] = None,
    ) -> Union[Dict[str, pd.DataFrame], pd.DataFrame]:
        """Return a Pandas dataframe from a given source.

        Accepts default pandas parameters for Excel and CSV, but the objective is to preserve the source data with
        little data conversion outside of the data wrangling process. With this in mind, a

        Parameters
        ----------
        source: str
            Source filename.
        preserve: str or list of str, default None
            Column names where variable type guessing must be prevented and the original data preserved.
            Critical for foreign key references with weird formats, like integers with leading `0`.
        filetype: MimeType, default MimeType.CSV
            Pandas can read a diversity of filetypes, but whyqd has only been tested on `xls`, `xlsx` and `csv`.
        names: list of str, default None
            If the source data has no header row, explicitly pass a list of names - in the correct order - to address
            the data.
        nrows: int, default None
            A specified number of rows to return. For review, it is faster to load only a small number.

        Returns
        -------
        DataFrame or dict of DataFrame
        """
        self.check_source(source)
        # If the dtypes have not been set, then ensure that any provided preserved columns remain untouched
        # i.e. no forcing of text to numbers
        # defaulting to `dtype = object` ...
        kwargs = {}
        if preserve:
            if not isinstance(preserve, list):
                preserve = [preserve]
            # kwargs["dtype"] = {k: object for k in preserve}
            kwargs["dtype"] = {k: pd.StringDtype() for k in preserve}
        if names:
            kwargs["header"] = None
            kwargs["names"] = names
        if nrows:
            kwargs["nrows"] = nrows
        # Check filetype
        if filetype in [MimeType.XLS, MimeType.XLSX]:
            # This will default to returning a dictionary of dataframes for each sheet
            kwargs["sheet_name"] = None
            df = pd.read_excel(source, **kwargs)
            keys = list(df.keys())
            for k in keys:
                if df[k].empty:
                    del df[k]
            if len(df.keys()) == 1:
                df = df[keys[0]]
        if filetype == MimeType.CSV:
            # New in pandas 1.3: will ignore encoding errors - perfect for this initial wrangling process
            kwargs["encoding_errors"] = "ignore"
            # Supposed to help with fruity separater guessing
            kwargs["engine"] = "python"
            if not nrows:
                df = pd.read_csv(source, **kwargs)
            else:
                kwargs["iterator"] = True
                kwargs["chunksize"] = 10000
                df_iterator = pd.read_csv(source, **kwargs)
                df = pd.concat(df_iterator, ignore_index=True)
        return df

    def get_dataframe_columns(self, df: pd.DataFrame) -> List(ColumnModel):
        """Returns a list of ColumnModels from a source DataFrame.

        Parameters
        ----------
        df: pd.DataFrame
            Should be derived from `get_dataframe` with a sensible default for `nrows` being 50.

        Returns
        -------
        List of ColumnModel
        """
        # Prepare summary
        columns = [
            {"name": k, "type": "number"}
            if v in ["float64", "int64"]
            else {"name": k, "type": "date"}
            if v in ["datetime64[ns]"]
            else {"name": k, "type": "string"}
            for k, v in df.dtypes.apply(lambda x: x.name).to_dict().items()
        ]
        return [ColumnModel(**c) for c in columns]

    def deduplicate_columns(self, df: pd.DataFrame, schema: Type[Schema]) -> pd.Index:
        """
        Source: https://stackoverflow.com/a/65254771/295606
        Source: https://stackoverflow.com/a/55405151
        Returns a new column list permitting deduplication of dataframes which may result from merge.

        Parameters
        ----------
        df: pd.DataFrame
        fields: list of FieldModel
            Destination Schema fields

        Returns
        -------
        pd.Index
            Updated column names
        """
        column_index = pd.Series(df.columns.tolist())
        if df.columns.has_duplicates:
            duplicates = column_index[column_index.duplicated()].unique()
            for name in duplicates:
                dups = column_index == name
                replacements = [f"{name}{i}" if i != 0 else name for i in range(dups.sum())]
                column_index.loc[dups] = replacements
        # Fix any fields with the same name as any of the target fields
        # Do this to 'force' schema assignment
        for name in [f.name for f in schema.get.fields]:
            dups = column_index == name
            replacements = [f"{name}{i}__dd" if i != 0 else f"{name}__dd" for i in range(dups.sum())]
            column_index.loc[dups] = replacements
        return pd.Index(column_index)

    def check_column_unique(self, source: str, key: str) -> bool:
        """
        Test a column in a dataframe to ensure all values are unique.

        Parameters
        ----------
        source: Source filename
        key: Column name of field where data are to be tested for uniqueness

        Raises
        ------
        ValueError if not unique

        Returns
        -------
        bool, True if unique
        """
        df = self.get_dataframe(source, key)
        if len(df[key]) != len(df[key].unique()):
            import warnings

            filename = source.split("/")[-1]  # Obfuscate the path
            e = "'{}' contains non-unique rows in column `{}`".format(filename, key)
            # raise ValueError(e)
            warnings.warn(e)
        return True

    def check_date_format(self, date_type: str, date_value: str) -> bool:
        # https://stackoverflow.com/a/37045601
        # https://www.saltycrane.com/blog/2009/05/converting-time-zones-datetime-objects-python/
        for fmt in self.DATE_FORMATS[date_type]["fmt"]:
            try:
                if date_value == datetime.strptime(date_value, fmt).strftime(fmt):
                    return True
            except ValueError:
                continue
        raise ValueError(f"Incorrect date format, should be: `{self.DATE_FORMATS[date_type]['txt']}`")

    ###################################################################################################
    ### Pandas type parsers
    ###################################################################################################

    def parse_dates(self, x: Union[None, str]) -> Union[pd.NaT, date.isoformat]:
        """
        This is the hard-won 'trust nobody', certainly not Americans, date parser.

        TODO: Replace with https://github.com/scrapinghub/dateparser
              The only concern is that dateparser.parse(x).date().isoformat() will coerce *any* string to a date,
              no matter *what* it is.
        """
        if pd.isnull(x):
            return pd.NaT
        # Check if to_datetime can handle things
        if not pd.isnull(pd.to_datetime(x, errors="coerce", dayfirst=True)):
            return date.isoformat(pd.to_datetime(x, errors="coerce", dayfirst=True))
        # Manually see if coersion will work
        x = str(x).strip()[:10]
        x = re.sub(r"[\\/,\.]", "-", x)
        try:
            y, m, d = x.split("-")
        except ValueError:
            return pd.NaT
        if len(y) < 4:
            # Swap the day and year positions
            # Ignore US dates
            d, m, y = x.split("-")
        # Fat finger on 1999 ... not going to check for other date errors as no way to figure out
        if y[0] == "9":
            y = "1" + y[1:]
        x = "{}-{}-{}".format(y, m, d)
        try:
            x = datetime.strptime(x, "%Y-%m-%d")
        except ValueError:
            return pd.NaT
        x = date.isoformat(x)
        try:
            pd.Timestamp(x)
            return x
        except pd.errors.OutOfBoundsDatetime:
            return pd.NaT

    def parse_float(self, x: Union[str, int, float]) -> Union[np.nan, float]:
        """
        Regex to extract wrecked floats: https://stackoverflow.com/a/385597
        Checked against: https://regex101.com/
        """
        try:
            return float(x)
        except ValueError:
            re_float = re.compile(
                r"""(?x)
            ^
                \D*     		# first, match an optional sign *and space*
                (             # then match integers or f.p. mantissas:
                    \d+       # start out with a ...
                    (
                        \.\d* # mantissa of the form a.b or a.
                    )?        # ? takes care of integers of the form a
                    |\.\d+     # mantissa of the form .b
                )
                ([eE][+-]?\d+)?  # finally, optionally match an exponent
            $"""
            )
            try:
                x = re_float.match(x).group(1)
                x = re.sub(r"[^e0-9,-\.]", "", str(x))
                return locale.atof(x)
            except (ValueError, AttributeError):
                return np.nan
