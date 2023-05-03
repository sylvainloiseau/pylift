from lift import LiftDoc, LiftLevel, LiftField, LiftVocabulary
import pytest
import lxml.etree as ET
from typing import List, Dict
import pandas as pd
import collections
import logging

LOGGER = logging.getLogger(__name__)


def test_get_frequencies_wo_subfield(caplog) -> None:
    """
   Without the subfield arg, must return a dict {subflied -> collections.Counter}
   """
    caplog.set_level(logging.INFO)
    lift: LiftDoc = LiftDoc("tests/data/tiny.lift")
    f = lift.get_frequencies(LiftVocabulary.LIFT_FIELD_SPEC["form"])
    LOGGER.info(f)
    assert isinstance(f, dict)
    assert len(f) == 1
    counter = f["tww"]
    assert isinstance(counter, collections.Counter)
    assert len(counter) == 2
    assert counter["efe"] == 1


def test_get_frequencies_with_subfield() -> None:
    """
   Without the subfield arg, must return a dict {subflied -> collections.Counter}
   """
    lift: LiftDoc = LiftDoc("tests/data/tiny.lift")
    counter = lift.get_frequencies(LiftVocabulary.LIFT_FIELD_SPEC["form"], "tww")
    assert isinstance(counter, collections.Counter)
    assert len(counter) == 2
    assert counter["efe"] == 1


def test_get_frequencies_with_exception() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny.lift")
    with pytest.raises(Exception):
        counter = lift.get_frequencies(LiftVocabulary.LIFT_FIELD_SPEC["form"], "not_existing_subfield")


def test_get_value(capsys, tmp_path) -> None:
    lift: LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
    assert lift.get_n(LiftLevel.ENTRY) == 182

    val = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["ID"])
    assert len(val) == 182


# No field is clearly repeatable (with the same language)
# def test_get_value_with_aggregation(capsys, tmp_path):
#    lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
#    #assert not LiftVocabulary.LIFT_FIELD_SPEC["category"]["unique"] # otherwise the test is meaningless
#    val = lift.get_values("category")
#    #with open("testlist.txt", "w") as f:
#    #  print(val, file=f)
#    assert len(val) == 184

def test__test_singleton_inner_list() -> None:
    l1 = [["un"], ["deux"]]
    l2 = [["un", "unbis"], ["deux", "deuxbis"]]

    with pytest.raises(Exception):
        LiftDoc._test_singleton_inner_list(l2)

    LiftDoc._test_singleton_inner_list(l1)

def test__example_empty() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny_example_empty.lift")
    f = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["example"])
    n = lift.get_n(LiftLevel.EXAMPLE)
    assert len(f) == n

def test__example() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny_with_example.lift")
    f = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["example"])
    n = lift.get_n(LiftLevel.EXAMPLE)
    assert len(f) == n

def test__test_missing_entry_id() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny_sense_id_missing.lift")

    with pytest.raises(Exception):
        lift.get_parent_id(LiftLevel.SENSE)


def test_create_records() -> None:
    doc_string = """<lift>
    <entry>
     <note type="foobla">blabla</note>
    </entry>
    <entry>
     <note type="foo">bla</note>
    </entry>
    <entry>
     <note type="foo">bla</note>
     <note type="bar">bla</note>
    </entry>
    <entry>
     <note type="bar">bla</note>
    </entry>
    <entry>
     <note type="bar">bla</note>
    </entry>
    </lift>
    """
    doc = ET.fromstring(doc_string)
    levels = doc.xpath("/lift/entry")
    assert len(levels) == 5
    assert len(levels[2]) == 2
    node_by_levels = [e.xpath("note") for e in levels]
    assert sum([len(x) for x in node_by_levels]) == 6
    records = LiftDoc._create_records(node_by_levels, "string(@type)", "string(.)")
    assert len(records) == 6
    assert records[0][2] == "blabla"
    assert records[0][1] == "foobla"
    assert records[0][0] == 0


# def test__aggregate_values_with_same_key() -> None:
#     x: List[List[Dict[str, str]]] = [[{"lang": "eng", "value": "note1"}, {"lang": "eng", "value": "note2"}],
#                                      [{"lang": "eng", "value": "note3"}, {"lang": "eng", "value": "note4"},
#                                       {"lang": "fra", "value": "note5"}]]
#     y = LiftDoc._aggregate_values_with_same_key(x, "lang", ["eng", "fra"], "/")
#     assert len(y) == len(x)
#     assert len(y[0]) == 2
#     assert len(y[1]) == 2
#     assert "note1/note2" in str(y)


def test__get_values_UNIQUE() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny.lift")
    x = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["ID"])
    assert len(x) == lift.get_n(LiftLevel.ENTRY)
    assert isinstance(x, pd.DataFrame)
    # assert isinstance(x[0], str)


def test__get_values_UNIQUE_BY_OBJECT_LANG() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny.lift")
    x = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["form"])
    assert len(x) == lift.get_n(LiftLevel.ENTRY)
    assert isinstance(x, pd.DataFrame)
    assert x.iloc[0][("form", "tww")] == "efe"


def test__get_values_MULTIPLE_WITH_META_LANG() -> None:
    lift: LiftDoc = LiftDoc("tests/data/tiny_with_multiple_gloss.lift", inner_sep=" ~ ")
    x = lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["gloss"])
    assert isinstance(x, pd.DataFrame)
    assert len(x) == 4
    assert x.iloc[0][("gloss", "en")] == "road ~ path"

# def test__get_values_UNIQUE_BY_META_LANG():
#   lift:LiftDoc = LiftDoc("tests/data/tiny_sense_id_missing.lift")
#   lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["ID"])

# def test__get_values_UNIQUE_BY_TYPE():
#   lift:LiftDoc = LiftDoc("tests/data/tiny_sense_id_missing.lift")
#   lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["ID"])

# def test__get_values_MULTIPLE():
#   lift:LiftDoc = LiftDoc("tests/data/tiny_sense_id_missing.lift")
#   lift.get_values(LiftVocabulary.LIFT_FIELD_SPEC["ID"])
