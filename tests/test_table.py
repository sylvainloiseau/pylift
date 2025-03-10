from pylift.lift import LiftDoc, LiftLevel, LiftVocabulary, LiftFieldSpec
from pylift.table import TableSet, AggregatedTable
import pytest
import lxml.etree as ET
import sys
from typing import List

def test_basic_1_field_list(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype", "gloss"]))
   assert len(t.fields_by_level[LiftLevel.ENTRY]) == 3
   assert len(t.fields_by_level[LiftLevel.SENSE]) == 1


def test_short(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype"]))
   table = t.get_level_table(LiftLevel.ENTRY)
   assert table.shape[0] == lift.get_n(LiftLevel.ENTRY)


def test_convert_level_table_to_csv(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype"]))
   table = t.get_level_table(LiftLevel.ENTRY)
   table.to_csv("test.csv")


def test_convert_csv(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype"]))
   a = AggregatedTable(t)
   a.to_csv(tmp_path / "test_table_to_csv.csv")


def test_convert_cldf(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype"]))
   a = AggregatedTable(t)
   a.to_cldf_Wordlist("cldf")


def test_get_entry_table(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype","gloss"]))
   entry_table = t.get_level_table(LiftLevel.ENTRY)
   assert t.tables_by_level[LiftLevel.ENTRY].shape[0] == 182
   sense_table = t.get_level_table(LiftLevel.SENSE)
   assert t.tables_by_level[LiftLevel.SENSE].shape[0] == 184


def test_merge_aggregate(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/tiny.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype", "gloss"]))
   a = AggregatedTable(t, aggregate=True, inner_sep="|")
   table = a.get_table()
   table.to_csv("test_merge_aggr_tiny.csv")


def test_merge(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/tiny.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype", "gloss"]))
   a = AggregatedTable(t)
   table = a.get_table()
   table.to_csv("test_merge_tiny.csv")


def test_merge_large(capsys, tmp_path) -> None:
   lift:LiftDoc = LiftDoc("tests/data/FlexLiftExport.lift")
   t = TableSet(lift, _get_fields(["ID", "form", "morphtype", "gloss"]))
   a = AggregatedTable(t)
   t.get_level_table(LiftLevel.ENTRY).to_csv("test_entry.csv")
   t.get_level_table(LiftLevel.SENSE).to_csv("test_sense.csv")

   table = a.get_table()
   table.to_csv("test_aggr_large.csv")


def _get_fields(fieldnames:List[str]) -> List[LiftFieldSpec]:
   return [ LiftVocabulary.LIFT_FIELD_SPEC_DIC[fieldname] for fieldname in fieldnames]

