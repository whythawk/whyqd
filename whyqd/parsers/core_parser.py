from __future__ import annotations
import json
import sys
import hashlib
from urllib.parse import urlparse
from datetime import date, datetime
from pathlib import Path, PurePath

# import pandas as pd
import modin.pandas as pd
from pandas.util import hash_pandas_object
from typing import Dict
import locale

# from ..utilities.hashing import hash_pandas_object
from ..config.ray_init import ray_start

ray_start()

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
    # Readthedocs has a problem, but difficult to replicate
    locale.setlocale(locale.LC_ALL, "")


class CoreScript:
    """Core functions for file and path management, and general ad-hoc utilities."""

    ###################################################################################################
    ### AD-HOC UTILITIES
    ###################################################################################################

    def get_now(self):
        return date.isoformat(datetime.now())

    def chunks(self, lst: list, n: int) -> list:
        """Yield successive n-sized chunks from l."""
        # https://stackoverflow.com/a/976918/295606
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    ###################################################################################################
    ### PATH MANAGEMENT
    ###################################################################################################

    def check_path(self, directory: str) -> Path:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return Path(directory)

    def check_source(self, source: str) -> bool:
        if Path(source).exists():
            return True
        else:
            e = "Source at `{}` not found.".format(source)
            raise FileNotFoundError(e)

    def get_path(self) -> PurePath:
        # whyqd/core/common ... .parent.parent -> whyqd/
        return Path(__file__).resolve().parent.parent

    def check_uri(self, source: str) -> bool:
        # https://stackoverflow.com/a/38020041
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc, result.path])
        except ValueError:
            return False

    def rename_file(self, source: str, newname: str, add_suffix: bool = False) -> str:
        p = Path(source)
        if add_suffix:
            newname = "{}{}".format(newname, p.suffix)
        p.rename(Path(p.parent, newname))
        return newname

    def delete_file(self, source):
        try:
            assert sys.version_info >= (3, 8)
        except AssertionError:
            Path(source).unlink()
        else:
            Path(source).unlink(missing_ok=True)

    ###################################################################################################
    ### CHECKSUMS
    ###################################################################################################

    def get_checksum(self, source: str) -> str:
        # https://stackoverflow.com/a/47800021
        checksum = hashlib.blake2b()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                checksum.update(chunk)
        return checksum.hexdigest()

    def get_data_checksum(self, df: pd.DataFrame) -> str:
        # The destination data does not have a valid checksum for the file itself, only the data.
        df_checksum = hash_pandas_object(df._to_pandas(), index=True).values
        checksum = hashlib.blake2b
        return checksum(df_checksum).hexdigest()

    ###################################################################################################
    ### JSON & FILE LOAD & SAVE
    ###################################################################################################

    def load_json(self, source: str) -> Dict:
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
        self.check_source(source)
        with open(source, "r") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError:
                e = "File at `{}` not valid json.".format(source)
                raise json.decoder.JSONDecodeError(e)

    def save_json(self, data, source):
        """
        Save a dictionary as a json file.

        Parameters
        ----------
        data: dictionary to be saved
        source: the filename to open, including path

        Returns
        -------
        bool, True if saved.
        """
        with open(source, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True, default=str)
        return True

    def save_file(self, data: json, source: str) -> bool:
        """Save json to file.

        Parameters
        ----------
        data: dictionary to be saved
        source: the filename to open, including path

        Returns
        -------
        bool, True if saved.
        """
        with open(source, "w") as f:
            f.write(data)
        return True
