from __future__ import annotations
from pathlib import Path
from typing import List, Type, TYPE_CHECKING

from ..parsers import CoreScript, ParserScript

if TYPE_CHECKING:
    from ..schema import Schema


class LegacyScript:
    """Parsing legacy Schema and Method json files into the current version."""

    def __init__(self) -> None:
        self.core = CoreScript()
        self.parser = ParserScript()

    def parse_legacy_method(self, version: str, schema: Type[Schema], source_path: str) -> List[str]:
        """Convert `method.json` files from Whyqd version 0.1 into a list of action scripts.

        Paramaters
        ----------
        version: str
            A member of a valid previous version.
        schema: Schema class object
        source_path: str
            Path to load the method.

        Returns
        -------
        list of str
        """
        self.core.check_source(source_path)
        source_path = Path(source_path)
        if version in ["0", "1"]:
            return self.generate_scripts_from_method_v0(schema, source_path)
        else:
            raise ValueError(f"Version provided ({version}) is not valid.")

    def generate_scripts_from_method_v0(self, schema: Type[Schema], source_path: Path) -> List[str]:
        """Convert `method.json` files from Whyqd version 0.1 into a list of scripts.

        Paramaters
        ----------
        schema: Schema class object
        method_path: str
            Path to load the version 0.1 json method.

        Returns
        -------
        list of str
        """
        method = self.core.load_json(source_path)
        # SCHEMA SCRIPTS
        schema_scripts = []
        for fld in method["fields"]:
            dstn = schema.get_field(fld["name"])
            actn = self.parser.get_action_model(fld["structure"][0]["name"])
            src_strctr = ""
            cat_scrpt = []
            if actn.structure and actn.name != "NEW":
                strct = []
                for src_trms in self.core.chunks(fld["structure"][1:], len(actn.structure)):
                    src_trms = [f"'{s['name']}'" if s["type"] != "modifier" else s["name"] for s in src_trms]
                    strct.append(" ".join(src_trms))
                src_strctr = f" < [{', '.join(strct)}]"
                # CATEGORISE
                if actn.name == "CATEGORISE":
                    cat_actn = "ASSIGN_CATEGORY_UNIQUES"
                    is_bool = False
                    if src_trms[0] == "-":
                        cat_actn = "ASSIGN_CATEGORY_BOOLEANS"
                        is_bool = True
                    for cat_inpt in fld["category"]["assigned"]:
                        cat_name = cat_inpt["name"]
                        if fld["type"] != "boolean":
                            cat_name = f"'{cat_name}'"
                        for cti in cat_inpt["category_input"]:
                            if not is_bool:
                                uniques = "', '".join(cti["terms"])
                                ct_scrp = f"{cat_actn} > '{dstn.name}'::{cat_name} < '{cti['column']}'::['{uniques}']"
                            else:
                                ct_scrp = f"{cat_actn} > '{dstn.name}'::{cat_name} < '{cti['column']}'"
                            cat_scrpt.append(ct_scrp)
            elif actn.name == "NEW":
                # NEW is special and needs to update the schema ...
                src_strctr = f" < ['{fld['structure'][1]['value']}']"
            scrpt = f"{actn.name} > '{dstn.name}'{src_strctr}"
            schema_scripts.append(scrpt)
            if cat_scrpt:
                schema_scripts.extend(cat_scrpt)
        return schema_scripts
