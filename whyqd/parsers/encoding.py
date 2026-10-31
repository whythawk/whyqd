# SPDX-License-Identifier: BSD-3-Clause
import codecs
import warnings
from collections import Counter

from whyqd.config.settings import settings
from whyqd.dtypes import EncodingStep


class EncodingParser:
    """A file's bytes as text, decoded as the WHATWG Encoding Standard decodes them, which CSV on the Web names its
    encodings by ([Encoding Standard](https://encoding.spec.whatwg.org/)).

    Nothing is guessed. The ladder: a byte-order mark, over any declaration; otherwise the declared encoding; otherwise
    strict UTF-8; otherwise `windows-1252`, which decodes every byte and loses none. A file in another encoding then
    loads with every byte kept, and reads as its text once the wrangler declares its encoding.
    """

    BOMS = ((b"\xef\xbb\xbf", "utf-8"), (b"\xfe\xff", "utf-16be"), (b"\xff\xfe", "utf-16le"))
    # Python's `cp1252` leaves five bytes undefined, which the standard decodes to the code point of their value
    WINDOWS_1252 = "".join(
        chr(b) if b in (0x81, 0x8D, 0x8F, 0x90, 0x9D) else bytes([b]).decode("cp1252") for b in range(256)
    )

    def name(self, *, label: str) -> str:
        """The standard's name, in lower case, for an encoding's label.

        Raises
        ------
        ValueError
            For a label of an encoding this whyqd does not decode, naming those it does.

        Example
        -------
        ```python
        EncodingParser().name(label="Latin1")   # "windows-1252"
        ```
        """
        label = label.strip().lower()
        for name, encoding in settings.ENCODINGS.items():
            if label in encoding["labels"]:
                return name
        raise ValueError(
            f"whyqd does not decode `{label}`. Declare one of {', '.join(settings.ENCODINGS)}, or no encoding. "
            "[whyqd:encoding-unknown]"
        )

    def decode(self, *, data: bytes, declared: str | None = None, source: str = "The file") -> tuple[str, str, EncodingStep]:
        """A file's text, the encoding that decoded it, and the step that settled it.

        A declared encoding that cannot decode some bytes still loads: each such byte reads as U+FFFD, as the standard's
        replacement mode reads it, and one warning says how many, and what to declare instead.

        Parameters
        ----------
        data: bytes
            The file.
        declared: str | None, default None
            The encoding the wrangler declared, by any of its labels.
        source: str, default "The file"
            The file's name, for the warning.

        Returns
        -------
        tuple[str, str, EncodingStep]
            The text, the encoding's name, and the step.
        """
        for mark, name in self.BOMS:
            if data.startswith(mark):
                return self.read(data=data[len(mark):], name=name, source=source), name, EncodingStep.BOM
        if declared is not None:
            name = self.name(label=declared)
            return self.read(data=data, name=name, source=source), name, EncodingStep.DECLARED
        try:
            return data.decode("utf-8"), "utf-8", EncodingStep.UTF8
        except UnicodeDecodeError:
            return self.read(data=data, name="windows-1252"), "windows-1252", EncodingStep.WINDOWS_1252

    def read(self, *, data: bytes, name: str, source: str = "The file") -> str:
        if name == "windows-1252":
            return codecs.charmap_decode(data, "strict", self.WINDOWS_1252)[0]
        codec = settings.ENCODINGS[name]["codec"]
        text, replaced, start, view = [], [], 0, memoryview(data)
        while True:
            try:
                text.append(codecs.decode(view[start:], codec))
                break
            except UnicodeDecodeError as e:
                text.append(codecs.decode(view[start : start + e.start], codec))
                replaced.append((start + e.start, bytes(view[start + e.start : start + e.end])))
                text.append("�")
                start += e.end
        if replaced:
            self.warn(data=data, name=name, replaced=replaced, source=source)
        return "".join(text)

    def warn(self, *, data: bytes, name: str, replaced: list[tuple[int, bytes]], source: str) -> None:
        line = {}
        for position, value in replaced:
            if value not in line:
                line[value] = data.count(b"\n", 0, position) + 1
        commonest = ", ".join(
            f"{value.hex(' ').upper()} ({count}, first on line {line[value]})"
            for value, count in Counter(v for _, v in replaced).most_common(3)
        )
        warnings.warn(
            f"{source} is declared `{name}`, but {len(replaced)} of its bytes are not, and read as � (commonest: "
            f"{commonest}). Declare its own encoding, most often `windows-1252`. [whyqd:encoding-replaced]",
            UserWarning,
            stacklevel=2,
        )
