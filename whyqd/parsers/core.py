from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import Json
import json
import sys
import hashlib
from urllib.parse import urlparse
import urllib
import posixpath
from uuid import uuid4
from datetime import date, datetime
from pathlib import Path, PurePath
import modin.pandas as pd
import numpy as np

# from pandas.util import hash_pandas_object
import locale
import randomname
import warnings

from whyqd.config.settings import settings

if TYPE_CHECKING:
    from whyqd.models import SchemaModel, CrosswalkModel

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
    # Readthedocs has a problem, but difficult to replicate
    locale.setlocale(locale.LC_ALL, "")


class CoreParser:
    """Core functions for file and path management, and general ad-hoc utilities."""

    def __init__(self) -> None:
        self.default_directory = settings.WHYQD_DIRECTORY

    ###################################################################################################
    ### AD-HOC UTILITIES
    ###################################################################################################

    def get_now(self):
        return date.isoformat(datetime.now())

    def chunks(self, *, lst: list, n: int) -> list:
        """Yield successive n-sized chunks from l."""
        # https://stackoverflow.com/a/976918/295606
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    def show_warning(self, message: str) -> None:
        warnings.warn(message, UserWarning)

    ###################################################################################################
    ### MODEL UTILITIES
    ###################################################################################################

    def create_or_update_model(
        self,
        *,
        modelType: type[SchemaModel] | type[CrosswalkModel],
        source: Path | str | SchemaModel | CrosswalkModel | None = None,
        model: SchemaModel | CrosswalkModel | None = None,
    ) -> SchemaModel | CrosswalkModel:
        """Update or create a model. Must have a default `name` field as the only dependency.

        Parameters
        ----------
        modelType: type of SchemaModel, CrosswalkModel
            The Pydantic function for the model type.
        source: Path, str or modelType, default None
            Any approach to loading a source.
        model: modelType, default None
            An existing model to be updated.
        """
        # Create a temporary model
        if not source:
            updated_model = modelType(**{"name": randomname.get_name()})
        else:
            if isinstance(source, (Path, str)):
                updated_model = modelType(**self.load_json(source=source))
            elif isinstance(source, (Json, dict)):
                updated_model = modelType(**source)
            elif isinstance(source, modelType):
                updated_model = source
            else:
                raise ValueError(
                    "`source` must either be a path to a source file, or a dictionary conforming to the model type."
                )
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        # Which doesn't really work properly as it returns dictionaries ... validation / init doesn't happen
        # This approach may be less efficient, but it does actually parse
        if model:
            model = model.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
            model |= updated_model.model_dump(exclude_unset=True)
            return modelType(**model)
        else:
            return updated_model

    ###################################################################################################
    ### PATH MANAGEMENT
    ###################################################################################################

    def check_path(self, *, directory: str, mode: oct = 0o777) -> Path:
        if isinstance(directory, str):
            directory = Path(directory)
        directory.mkdir(mode=mode, parents=True, exist_ok=True)
        return directory

    def check_source(self, *, source: str) -> bool:
        if isinstance(source, str):
            source = Path(source)
        return source.exists()

    def get_path(self) -> PurePath:
        # whyqd/core/common ... .parent.parent -> whyqd/
        return Path(__file__).resolve().parent.parent

    def check_uri(self, *, source: str) -> bool:
        # https://stackoverflow.com/a/38020041
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc, result.path])
        except (ValueError, AttributeError):
            return False

    def check_path_or_uri(self, *, source: str) -> bool:
        if not isinstance(source, str):
            source = str(source)
        return any([Path(source).exists(), self.check_uri(source=source)])

    def rename_file(self, *, source: str, newname: str, add_suffix: bool = False) -> str:
        p = Path(source)
        if add_suffix:
            newname = f"{newname}.{p.suffix}"
        p.rename(Path(p.parent, newname))
        return newname

    def delete_file(self, *, source: Path | str):
        if isinstance(source, str):
            source = Path(source)
        try:
            assert sys.version_info >= (3, 8)
        except AssertionError:
            source.unlink()
        else:
            source.unlink(missing_ok=True)

    def download_uri_source(self, source: str, directory: Path | str | None = None) -> Path:
        """Downloads a source at a remote uri, and returns a Path for that downloaded source.

        Parameters
        ----------
        source: str
            URI path to source.
        directory: Path | str | None

        Returns
        -------
        Path to local source.
        """
        request = urllib.request.Request(source, method="HEAD")
        request = urllib.request.urlopen(request).info()
        filename = request.get_filename()
        if not filename:
            #  https://stackoverflow.com/a/11783319/295606
            source_path = urllib.request.urlsplit(source).path
            filename = posixpath.basename(source_path)
        if not filename:
            # Make something up ...
            filename = f"temporary-{uuid4()}"
        if not directory:
            directory = self.default_directory
        local_source = Path(directory) / filename
        if not self.check_source(source=local_source):
            urllib.request.urlretrieve(source, local_source)
        return local_source

    ###################################################################################################
    ### CHECKSUMS
    ###################################################################################################

    def get_checksum(self, *, source: str) -> str:
        # https://stackoverflow.com/a/47800021
        checksum = hashlib.blake2b()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                checksum.update(chunk)
        return checksum.hexdigest()

    def get_data_checksum(self, *, df: pd.DataFrame) -> str:
        # The destination data does not have a valid checksum for the file itself, only the data.
        # df_checksum = hash_pandas_object(df.astype("string")._to_pandas(), index=True).values
        # Need to ensure arrays are all of the same type. Easiest is to coerce np arrays to lists
        for column in df.columns:
            if isinstance(df.iloc[0][column], np.ndarray):
                df[column] = df[column].apply(lambda x: x.tolist())
        df_string = df.astype("string").astype("string").to_string(index=False).encode("utf-8")
        checksum = hashlib.blake2b
        return checksum(df_string).hexdigest()

    ###################################################################################################
    ### JSON & FILE LOAD & SAVE
    ###################################################################################################

    def load_json(self, *, source: str) -> dict:
        """
        Load and return a JSON file, if it exists.

        Paramaters
        ----------
        source: the filename & path to open

        Raises
        ------
        JSONDecoderError if not a valid json file
        FileNotFoundError if not a valid source

        Returns
        -------
        dict
        """
        with open(source, "r") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError:
                e = "File at `{}` not valid json.".format(source)
                raise json.decoder.JSONDecodeError(e)

    def save_json(self, *, data: dict, source: str) -> bool:
        """
        Save a dictionary as a json file.

        Parameters
        ----------
        data: dictionary to be saved
        source: the filename to save, including path

        Returns
        -------
        bool, True if saved.
        """
        with open(source, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True, default=str)
        return True

    def save_file(self, *, data: json, source: str) -> bool:
        """Save json to file.

        Parameters
        ----------
        data: dictionary to be saved
        source: the filename to save, including path

        Returns
        -------
        bool, True if saved.
        """
        with open(source, "w") as f:
            f.write(data)
        return True
