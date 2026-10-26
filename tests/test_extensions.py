# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

import pytest

import whyqd as qd
from whyqd.parsers.extension import ExtensionParser

DIRECTORY = Path(__file__).resolve().parent / "data"
CROSSWALK = DIRECTORY / "test_crosswalk.crosswalk"
SCHEMA = DIRECTORY / "test_schema.schema"


def install(root: Path, distribution: str, version: str, entry_points: dict[str, list[str]]) -> None:
    """A package as importlib.metadata finds one installed: its `.dist-info` folder, with its entry points."""
    info = root / f"{distribution.replace('-', '_')}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {distribution}\nVersion: {version}\n")
    groups = [
        f"[{group}]\n" + "".join(f"{name} = {distribution.replace('-', '_')}:Extension\n" for name in names)
        for group, names in entry_points.items()
    ]
    (info / "entry_points.txt").write_text("\n".join(groups))


@pytest.fixture
def installed(tmp_path, monkeypatch):
    install(tmp_path, "whyqd-postal", "1.4.0", {"whyqd.actions": ["NORMALISE_ADDRESS"], "whyqd.types": ["postcode"]})
    install(tmp_path, "whyqd-geo", "2.0.0rc1", {"whyqd.actions": ["GEOCODE", "NORMALISE_ADDRESS"]})
    monkeypatch.syspath_prepend(str(tmp_path))
    return ExtensionParser()


def declaration(**changes) -> dict:
    return {"name": "NORMALISE_ADDRESS", "kind": "action", "distribution": "whyqd-postal", "version": ">=1.4,<2"} | (
        changes
    )


def crosswalk(*extensions: dict) -> dict:
    model = json.loads(qd.CrosswalkDefinition(crosswalk=CROSSWALK).get_json())
    model["extensions"] = list(extensions)
    return model


class TestDeclare:
    def test_fills_its_range(self, installed):
        declared = installed.declare(name="postcode", kind="type")
        assert (declared.distribution, declared.version) == ("whyqd-postal", ">=1.4.0,<2")

    def test_two_providers_need_naming(self, installed):
        with pytest.raises(ValueError, match="whyqd-postal.*whyqd-geo|whyqd-geo.*whyqd-postal"):
            installed.declare(name="NORMALISE_ADDRESS", kind="action")
        assert installed.declare(name="NORMALISE_ADDRESS", kind="action", distribution="whyqd-geo").version == (
            ">=2.0.0rc1,<3"
        )

    def test_missing_refused(self, installed):
        with pytest.raises(ValueError, match="No installed package provides the action `TRANSLATE`"):
            installed.declare(name="TRANSLATE", kind="action")


class TestCheck:
    def test_declared_and_installed_reads(self, installed):
        written = json.loads(qd.CrosswalkDefinition(crosswalk=crosswalk(declaration())).get_json())
        assert written["extensions"] == [declaration()]

    def test_type_on_a_schema_reads(self, installed):
        model = json.loads(qd.SchemaDefinition(source=SCHEMA).get_json())
        model["extensions"] = [declaration(name="postcode", kind="type")]
        assert qd.SchemaDefinition(source=model).get.extensions[0].name == "postcode"

    def test_installed_pre_release_in_range(self, installed):
        qd.CrosswalkDefinition(crosswalk=crosswalk(declaration(distribution="whyqd-geo", version=">=1,<3")))

    @pytest.mark.parametrize(
        "extensions, refusal",
        [
            ([declaration(distribution="whyqd-absent")], "needs `whyqd-absent`, which is not installed"),
            ([declaration(version=">=2,<3")], r"needs `whyqd-postal` >=2,<3, and 1\.4\.0 is installed"),
            ([declaration(), declaration(distribution="whyqd-geo", version=">=2.0.0rc1")], "declared 2 times"),
            ([declaration(name="RENAME")], "one of whyqd's own"),
            ([declaration(name="string", kind="type")], "one of whyqd's own"),
            ([declaration(name="GEOCODE")], "does not provide the action `GEOCODE`"),
            ([declaration(version="1.4")], "not a version specifier"),
        ],
        ids=["missing", "outside range", "twice", "built-in action", "built-in type", "not provided", "bad range"],
    )
    def test_refused(self, installed, extensions, refusal):
        with pytest.raises(ValueError, match=refusal):
            qd.CrosswalkDefinition(crosswalk=crosswalk(*extensions))

    def test_checked_inside_a_transform(self, installed):
        transform = {"name": "embedded", "crosswalk": crosswalk(declaration(version=">=2,<3"))}
        with pytest.raises(ValueError, match="1.4.0 is installed"):
            qd.TransformDefinition(transform=transform)

    def test_transform_record_not_checked(self, installed):
        record = declaration(distribution="whyqd-absent", version="==0.9.1")
        assert qd.TransformDefinition(transform={"name": "ran", "extensions": [record]}).get.extensions[0].version == (
            "==0.9.1"
        )

    def test_1x_save_refused(self, installed):
        definition = qd.CrosswalkDefinition(crosswalk=crosswalk(declaration()))
        with pytest.raises(ValueError, match=r"`extensions`.*1\.x cannot hold it"):
            definition.get_json(format="1.x")
