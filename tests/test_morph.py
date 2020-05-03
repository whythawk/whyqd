from pathlib import Path
import os

import whyqd as _w
from whyqd.core import common as _c
from whyqd.morph import morphs, default_morphs

working_data = "/data/working_test_world_bank_data.xlsx"
DIRECTORY = str(Path(__file__).resolve().parent)
DF = _c.get_dataframe(DIRECTORY + working_data, dtype=object)

class TestMorph:

    def test_deblank(self):
        mrph = "DEBLANK"
        mrph = morphs[mrph]()
        assert mrph.validates(DF.copy(deep=True))
        mrph.transform(DF.copy(deep=True))

    def test_dedupe(self):
        mrph = "DEDUPE"
        mrph = morphs[mrph]()
        assert mrph.validates(DF.copy(deep=True))
        mrph.transform(DF.copy(deep=True))

    def test_many(self):
        ############################
        mrph = "REBASE"
        mrph = morphs[mrph]()
        assert mrph.validates(DF.copy(deep=True), 2)
        parameters = dict(zip(mrph.structure, mrph.parameters))
        dfm = mrph.transform(DF.copy(deep=True), **parameters)
        ############################
        mrph = "MELT"
        mrph = morphs[mrph]()
        parameters = dict(zip(mrph.structure, [[list(dfm.columns[:4]), list(dfm.columns[4:])]]))
        assert mrph.validates(dfm, **parameters)
        parameters = dict(zip(mrph.structure, mrph.parameters))
        dfm = mrph.transform(dfm, **parameters)
        ############################
        mrph = "RENAME"
        mrph = morphs[mrph]()
        parameters = dict(zip(mrph.structure, [["country_code", "country_name", 
                                               "indicator_code", "indicator_name", 
                                               "year", "values"]]))
        assert mrph.validates(dfm, **parameters)
        parameters = dict(zip(mrph.structure, mrph.parameters))
        dfm = mrph.transform(dfm, **parameters)
        ############################
        mrph = "DELETE"
        mrph = morphs[mrph]()
        parameters = dict(zip(mrph.structure, [[5, 7, 9]]))
        assert mrph.validates(dfm, **parameters)
        parameters = dict(zip(mrph.structure, mrph.parameters))
        dfm = mrph.transform(dfm, **parameters)