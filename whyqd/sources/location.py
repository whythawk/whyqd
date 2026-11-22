# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
from urllib.parse import urlparse, urlsplit
from uuid import uuid4
import posixpath
import urllib.request

from whyqd.config.settings import settings


class LocationParser:
    """Where a source's file is: a local path as given, or a URI's file downloaded first."""

    def locate(self, *, source: str | Path, directory: str | Path | None = None) -> Path:
        """The local path of a source, downloading one given by URI.

        Parameters:
            source: A file's path, or a URI with a scheme, a host, and a path.
            directory: Where to download a URI's file; `settings.WHYQD_DIRECTORY` where `None`.

        Raises:
            FileNotFoundError: Where no file is there.

        Examples:
            ```python
            LocationParser().locate(source="data/rates.csv")   # Path("data/rates.csv")
            ```
        """
        if self.is_uri(source=source):
            source = self.download(source=source, directory=directory)
        if not Path(source).exists():
            raise FileNotFoundError(f"No file at `{source}`. [whyqd:source-missing]")
        return Path(source)

    def is_uri(self, *, source: str | Path) -> bool:
        """Whether a source is a URI: a scheme, a host, and a path. A `Path` never is."""
        try:
            parts = urlparse(source)
            return all([parts.scheme, parts.netloc, parts.path])
        except (ValueError, AttributeError):
            return False

    def download(self, *, source: str, directory: str | Path | None = None) -> Path:
        """A URI's file, downloaded to `directory` unless a file of its name is already there.

        The file takes the name its server gives, else the URI's last part, else a made-up one.
        """
        filename = urllib.request.urlopen(urllib.request.Request(source, method="HEAD")).info().get_filename()
        if not filename:
            filename = posixpath.basename(urlsplit(source).path)
        if not filename:
            filename = f"temporary-{uuid4()}"
        local = Path(directory or settings.WHYQD_DIRECTORY) / filename
        if not local.exists():
            urllib.request.urlretrieve(source, local)
        return local
