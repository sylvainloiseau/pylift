from pylift.lift import LiftDoc, LiftLevel, LiftVocabulary, LiftField
from typing import List
import pandas as pd
from cldfbench import CLDFSpec, CLDFWriter
import logging

LOGGER = logging.getLogger(__name__)


class TableSet:
    """
  A representation of the dictionary as a set of linked tables, each representing a lift level (:class:`LiftLevel`).
  """

    def __init__(self, lift: LiftDoc, fields: List[LiftField]):
        """
    Create a table set defined by a specification of the kind of data to be extracted from a lift document.
    :param lift: a lift document (:class: `LiftDoc`)
    :param fields: the data to extract from the dictionary (see `LiftVocabulary.LIFT_FIELD_SPEC`)
    """
        self.lift = lift
        self.fields = fields

        if fields is None or len(fields) < 1:
            raise ValueError("No field received")

        # all_levels =[e for e in LiftLevel]
        # from low to top levels
        all_levels_sorted = [LiftLevel.EXAMPLE, LiftLevel.SENSE, LiftLevel.VARIANT, LiftLevel.ENTRY]

        self.fields_by_level = {
            level: [field for field in fields if field.level == level]
            for level in all_levels_sorted
        }
        used_levels = [level for level in all_levels_sorted if len(self.fields_by_level[level]) > 0]

        self.tables_by_level = {u_level: None for u_level in used_levels}

        for u_level in used_levels:
            self._create_table(u_level)

    def get_level_table(self, level: LiftLevel) -> pd.DataFrame:
        return self.tables_by_level[level]

    def _create_table(self, level: LiftLevel) -> None:
        # TODO resume here
        # verify_integrity
        # x = [LiftVocabulary.LIFT_FIELD_SPEC[f]["unique"] for f in self.fields_by_level[level]]

        n = self.lift.get_n(level)
        index = list(range(0, n))
        table = pd.DataFrame()
        table.index = index
        table.columns = pd.MultiIndex.from_arrays([[], []], names=["field", "subfield"])

        LOGGER.info(f"Creating table for level '{str(level)}'")
        for field in self.fields_by_level[level]:
            fvalue = self.lift.get_values(field)
            assert len(fvalue) == len(table)
            # TODO: get_values() does not return list anymore
            if isinstance(fvalue, list):
                table[field.name, ""] = fvalue
            else:
                # field           gloss
                # lang               en
                # index
                # 0         road ~ path
                # 1         skin ~ bark
                # 2      paddle ~ drift
                # 3         swim ~ wash
                table = table.join(fvalue, rsuffix=field)  # left join, on index value
            LOGGER.info(f"field '{field.name}' added with {fvalue.shape[0]} values")

        # add id of parent on each row
        if level != LiftLevel.ENTRY:
            table["parent_id"] = self.lift.get_parent_id(level)
        else:
            table["ID"] = self.lift.get_id(level)

        self.tables_by_level[level] = table


class AggregatedTable:
    """
  Turn a set of linked tables into a single table, by aggregating child values
  (concatenating the rows of a table that refer to the same row of another table)
  or duplicating parent values.
  """

    def __init__(self, table_set: TableSet, aggregate: bool = False, inner_sep=";"):
        self.table_set = table_set
        self.inner_sep = inner_sep

        if (len(self.table_set.fields_by_level[LiftLevel.VARIANT]) > 0) and (
                len(self.table_set.fields_by_level[LiftLevel.SENSE]) > 0):
            raise Exception(
                "Cannot create table with data from both senses and variantes (several senses and several variants "
                "can exist for an entry)")

        # all_levels =[e for e in LiftLevel]
        # from low to top levels
        # TODO: duplicated
        all_levels_sorted = [LiftLevel.EXAMPLE, LiftLevel.SENSE, LiftLevel.VARIANT, LiftLevel.ENTRY]

        levels_sorted = [l for l in all_levels_sorted if l in table_set.tables_by_level]
        tables_sorted = [table_set.tables_by_level[l] for l in levels_sorted]

        if len(table_set.tables_by_level) == 1:
            self.res = tables_sorted[0]
            return

        merged = None
        for i, t in enumerate(tables_sorted):  # enumerate starts at 0
            if i + 1 < len(tables_sorted):  # if this is not the last table
                if aggregate:
                    t = self._group_by_parent_id(levels_sorted[i])
                merged = tables_sorted[i + 1].merge(t, left_on="ID", right_on="parent_id")
        self.res = merged

    def get_table(self) -> pd.DataFrame:
        return self.res

    def to_csv(self, filename: str) -> None:
        """
    Write the table as a CSV file
    :param filename: the destination
    """
        self.res.to_csv(filename)

    def to_cldf_Wordlist(self, dir_name: str) -> None:
        """
    Turn the table into a CLDF dataset of type "Wordlist"
    :param dir_name: the directory where the dataset is written.
    """
        spec = CLDFSpec(dir=dir_name, module="Wordlist", metadata_fname="metadata.json")
        with CLDFWriter(spec) as writer:
            # writer.cldf.add_component("FormTable")
            rowdict = self.res.to_dict(orient='records')
            for entry in rowdict:
                # key are tuple, due to the multiindex in the table
                single_index = {}
                for k, v in entry.items():
                    if k[0] == "form":
                        single_index["Form"] = v
                        single_index["Language_ID"] = k[1]
                    if k[0] == "gloss":
                        single_index["Parameter_ID"] = v
                        # single_index["Language_ID"] = k[1]
                    else:
                        single_index["".join(k)] = v
                writer.objects["FormTable"].append(single_index)

            writer.write()

    def _group_by_parent_id(self, level: LiftLevel) -> pd.DataFrame:
        """
    Aggregate row in a table that have the same parent
    (for instance various gloss, categories... (in the sense table) related to the same entries (in the entry table))
    """
        if self.table_set.fields_by_level[level] is None or len(self.table_set.fields_by_level[level]) == 0:
            raise Exception(f"cannot aggregate a table without column ({str(level)})")
        if level not in self.table_set.tables_by_level:
            raise Exception(f"table is not instantiated ({str(level)})")
        if self.table_set.tables_by_level[level].shape[0] == 0:
            raise Exception(f"cannot aggregate a table without row ({str(level)})")

        # aggregating_spec = {
        #     k:self.inner_sep.join for k in self.tableSet.fields_by_level[level]
        #   }
        tmp = self.table_set.tables_by_level[level]
        # tmp = tmp.groupby(by=('parent_id', ''), as_index = False).agg(aggregating_spec)

        tmp = tmp.groupby(by=('parent_id', ''), as_index=False).agg(lambda x: self.inner_sep.join(x))
        return tmp
