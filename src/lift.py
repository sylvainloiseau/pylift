from lxml import etree as ET
from typing import Union, List, Tuple, Dict, Set, cast
from io import StringIO
import pkgutil
import collections
from enum import Enum, IntEnum
from dataclasses import dataclass
import pandas as pd
import logging
import os

LOGGER = logging.getLogger(__name__)


class FieldType(Enum):
    """
  Field types distinguished in the LIFT schema:

  - some fields are unique (only one morph type for each lexical entry, only one ID for each lexical entry...)
  - Some fields can be repeated as long as they have a @lang attribute with different values:
       - eg. element "definition", or "lexical-unit" (see the "multitext-content" type in the RNG schema of lift document)
         in those cases, the element (eg "definition) contains an element "form" with the attribute @lang, that contains an element "text"
         (all elements "form" in LIFT documents are serving this purpose)
  - Some fields can be repeated as long as they have a @type attribute with different values:
       - eg. elements "note", "trait" (see the "field-content" type in the RNG schema of lift document)
         in those cases, the element (eg "note") contains an element "field" with the attribute @type
         (all elements "field" (but in the header element) are serving this purpose)
  - Some fields can be repeated without condition
       - e.g. element "?". The values for such field are concatenated into one string.
  - Some fields can be repeated but do have a @lang attribute
       - e.g. element "gloss" (contains an attribute @lang and an element text, but several gloss with the same value for @lang can exist)
         the values for such field are concatenated when there are several elements with the same value for @lang
  """

    UNIQUE = 1
    UNIQUE_BY_OBJECT_LANG = 2
    UNIQUE_BY_META_LANG = 3
    UNIQUE_BY_TYPE = 4
    MULTIPLE = 5
    MULTIPLE_WITH_META_LANG = 6


class LiftLevel(IntEnum):
    """
   Levels are ordered from top level to low level.
   """
    ENTRY = 1
    SENSE = 2
    EXAMPLE = 3
    VARIANT = 4


@dataclass(frozen=True)
class LiftField:
    """
  A lift field (i.e. a piece of information in the dictionary, such as the forms of the entries, or the glosses of the senses, etc.).
  A field is defined as:

  :param name: the name of the field, used for refering to the field from the command line or in outputs.
  :param node_xpath: an XPath expression, relative to the level node, and pointing to the nodes containing the value.\
    For instance the gloss field belongs to the sense level and is accessed through the XPath `gloss` (or `./gloss`)
  :param value_xpath: an XPath expression that can be wrapped into the `string()` XPath function and will return the \
    text content we are interested in. The XPath is relative to `node_xpath` nodes. \
    For the "gloss" field, the content is in a `./text` node.
  :param level: the level the field belongs to. The "gloss" field belongs to the sense level. See see :class:`LiftLevel`.
  :param field_type: the LIFT Schema defined different field types. See :class:`FieldType`. For instance, the "gloss" field\
    is of type `FieldType.MULTIPLE_WITH_META_LANG`, which means that there is an `@lang` attribute on the nodes referred\
    to through `node_xpath` nodes (here, `gloss`) that this attribute contains a reference to a language used in the description\
    and that several `gloss` element with the same `@lang` value are possible.
  :param mixed_content: if `True`, the `value_xpath` can contains other XML elements for inline formating (such as `span`).
  """
    name: str
    node_xpath: str
    value_xpath: str
    level: LiftLevel
    field_type: FieldType
    mixed_content: bool

class LiftVocabulary:
    LIFT_LEVEL_SPEC: Dict[LiftLevel, Dict[str, Union[str, LiftLevel]]] = {
        LiftLevel.ENTRY: {
            "xpath": "/lift/entry",
            "parent": ""
        },
        LiftLevel.SENSE: {
            "xpath": "/lift/entry/sense",
            "parent": LiftLevel.ENTRY,
            "parent_id": "./parent::entry/@id"
        },
        LiftLevel.EXAMPLE: {
            "xpath": "/lift/entry/sense/example",
            "parent": LiftLevel.SENSE,
            "parent_id": "./parent::sense/@id"
        },
        LiftLevel.VARIANT: {
            "xpath": "/lift/entry/variant",
            "parent": LiftLevel.ENTRY,
            "parent_id": "./parent::entry/@id"
        }
    }

    LIFT_FIELD_SPEC_LIST = [
        LiftField("ID",          ".",                         "@id",    LiftLevel.ENTRY,   FieldType.UNIQUE,                False),
        LiftField("form",        "lexical-unit/form",         "text",   LiftLevel.ENTRY,   FieldType.UNIQUE_BY_OBJECT_LANG, True),
        LiftField("variantform", "form",                      ".",      LiftLevel.VARIANT, FieldType.UNIQUE_BY_OBJECT_LANG, True),
        LiftField("morphtype",   "trait[@name='morph-type']", "@value", LiftLevel.ENTRY,   FieldType.UNIQUE,                False),
        LiftField("category",    "grammatical-info",          "@value", LiftLevel.SENSE,   FieldType.UNIQUE,                False),
        LiftField("gloss",       "gloss",                     "./text", LiftLevel.SENSE,   FieldType.MULTIPLE_WITH_META_LANG, True),
        LiftField("definition",  "definition/form",           ".",      LiftLevel.SENSE,   FieldType.UNIQUE_BY_META_LANG,   True),
        LiftField("example",     "./form",                    "./text", LiftLevel.EXAMPLE, FieldType.UNIQUE_BY_OBJECT_LANG, True),
        LiftField("ex_source",     ".",                       "@source", LiftLevel.EXAMPLE, FieldType.UNIQUE, True),
        LiftField("translation", "./translation/form",        "./text", LiftLevel.EXAMPLE, FieldType.UNIQUE_BY_META_LANG, True)
    ]

    LIFT_FIELD_SPEC = {field.name: field for field in LIFT_FIELD_SPEC_LIST}


class LiftDoc:
    """
  A document as an XML tree with methods for fetching the values of its fields, validating the XML content, and extracting basic information
  """

    def __init__(self, filename: str, inner_sep="/", validate=False):
        """
    :param filename: the Lift XML document file name
    :param inner_sep: the separator to be used when aggregating values of a fields \
      that have multiple values (for instance, several notes on the same entry).\
      see :class:`FieldType`, types `MULTIPLE` and `MULTIPLE_WITH_META_LANG`. 
    :param validate: `bool` flag signaling whether to validate the document
    """
        self.filename: str = filename
        self.inner_sep: str = inner_sep
        self.dictionary: ET._ElementTree = ET.parse(self.filename)
        self._cached_nodes_by_level: Dict[LiftLevel, List[ET.Element]] = {}
        self.object_languages: Set[str] = set(self.dictionary.xpath("/lift/entry//form/@lang"))
        self.meta_languages: Set[str] = set(self.dictionary.xpath("/lift/entry//*[local-name() != 'form']/@lang"))

        if validate:
            self.validation()

    def get_frequencies(self, field: LiftField, subfield: str = "") -> Union[
        collections.Counter, Dict[str, collections.Counter]]:
        """
    :param field: the field used for fetching values
    :param subfield: some field have several values for different langs or different types \
      In such cases, a subfield (giving a language or type) is necessary to compute a frequency list
      (see :class:`FieldType`, types `UNIQUE_BY_OBJECT_LANG`, `UNIQUE_BY_META_LANG`, \
      `UNIQUE_BY_TYPE` and `MULTIPLE_WITH_META_LANG`).
      If no subfield is given, several frequency lists are computed (one for each subtype)
    :return: a :class:`collections.Counter` or a dictionary that associates \
      the available subfields with a :class:`collections.Counter`.
    """
        items = self.get_values(field)
        items = items.iloc[:][(field.name)]
        if isinstance(items, pd.core.series.Series):
            return collections.Counter(items)
        elif isinstance(items, pd.core.frame.DataFrame):
            if subfield:
                if subfield not in items.columns:
                    raise Exception(f"Unknown subfield: {subfield}. Available subfields are: {','.join(items.columns)}")
                items = items.iloc[:][subfield]
                return collections.Counter(items)
            else:
                return {sub: collections.Counter(items.iloc[:][sub]) for sub in items.columns}
        else:
            raise Exception(f"Unknown type: {type(items)}")

    def get_n(self, level: LiftLevel) -> int:
        """
    The number of occurrences of the given level (:class:`LiftLevel`) in a document
    :param level: a (:class:`LiftLevel`)
    :return: the number of occurrences of the level
    """
        if level not in self._cached_nodes_by_level:
            self._cached_nodes_by_level[level] = self.dictionary.xpath(LiftVocabulary.LIFT_LEVEL_SPEC[level]["xpath"])
        return len(self._cached_nodes_by_level[level])

    def get_object_languages(self) -> Set[str]:
        """
    The object languages used in the document are the language codes used in `@lang`\
        attribute of `form` elements.
    :return: a set of languages code
    """
        return self.object_languages

    def get_meta_languages(self) -> Set[str]:
        """
    The meta languages used in the document are the language codes used in `@lang`\
        attribute of all elements but the `form` elements.
    :return: a set of languages code
    """
        return self.meta_languages

    def get_values(self, field: LiftField) -> pd.DataFrame:
        """
    Compute the list of the values for a given field: the list of form, gloss, etc.
    :return: a :class:`pd.DataFrame` containing each value, together with the indice \
      of the level it belongs to; some field may return a data frame with several columns,\
      corresponding to the values of the `@type` attributes or of the `@lang` attributes.\
      The data frame contains a multiIndex columns index, where the first level\
      give the field name and the second level the subfield name (lang or type), or
      an empty string if there is no subfield.
    """
        level = field.level

        # Collect the XML elements of the field.
        # A field can have several elements in the same level occurrence
        if level not in self._cached_nodes_by_level:
            self._cached_nodes_by_level[level] = self.dictionary.xpath(LiftVocabulary.LIFT_LEVEL_SPEC[level]["xpath"])
        level_nodes = self._cached_nodes_by_level[level]
        field_nodes_by_level_nodes = [e.xpath(field.node_xpath) for e in level_nodes]
        assert len(level_nodes) == len(field_nodes_by_level_nodes)

        # The xpath expression for retreiving the actual textual values
        # for each field element.
        field_value_xpath = f"string({field.value_xpath})"

        # Case where the returned DataFrame will always have a single column:
        # either the field has one element per entry (`FieldType.UNIQUE`),
        # or it may have several elements (`FieldType.MULTIPLE`),
        # but without `@lang` or `@type` to distinguish them, and the textual values are aggregated.
        if (field.field_type == FieldType.UNIQUE
                or field.field_type == FieldType.MULTIPLE):

            if field.field_type == FieldType.UNIQUE:
                # checking if each level element contains only one field element
                LiftDoc._test_singleton_inner_list(field_nodes_by_level_nodes)
                # either retreive the value, or we add an empty string if the result set is empty.
                values = [""] * len(field_nodes_by_level_nodes)
                for i, e in enumerate(field_nodes_by_level_nodes):
                    values[i] = e[0].xpath(field_value_xpath) if len(e) > 0 else ""
            elif field.field_type == FieldType.MULTIPLE:
                # aggregate multiple values of `FieldType.MULTIPLE` field
                values = [self.inner_sep.join(sublist) if len(sublist) > 0 else "" for sublist in
                          field_nodes_by_level_nodes]
            else:
                raise Exception("I shouldn't be here")

            assert len(values) == len(level_nodes)
            res = pd.DataFrame()
            res.columns = pd.MultiIndex.from_arrays([[], []], names=["field", "subfield"])
            res[field.name, ""] = values
            res.index = list(range(0, len(field_nodes_by_level_nodes)))  # range will stop at len()-1

        # Case where the returned DataFrame may have several columns:
        elif (field.field_type == FieldType.UNIQUE_BY_META_LANG
              or field.field_type == FieldType.UNIQUE_BY_OBJECT_LANG
              or field.field_type == FieldType.UNIQUE_BY_TYPE
              or field.field_type == FieldType.MULTIPLE_WITH_META_LANG):

            # Collect a list of tuples (key (@lang or @type), value (field text value))
            # for each field element (note, form) for each level entry (sense, or entry...)
            if field.field_type == FieldType.UNIQUE_BY_TYPE:
                key = "type"
            else:
                key = "lang"
            key_xpath = "string(@" + key + ")"
            record_tuples = LiftDoc._create_records(field_nodes_by_level_nodes, key_xpath, field_value_xpath)

            # turn this into a three columns dataframe:
            # level key value
            # ----- --- -----
            # 0     en  foo
            # 0     tww efe
            # 1     en  bar
            # ...
            df = pd.DataFrame(record_tuples, columns=["index", key, "value"])
            df[key] = df[key].astype("category")
            key_values = df[key].unique()

            # In the case where several field element may have both the level occurrence and the same key
            # (here, object lang), the nodes content must be aggregated
            if field.field_type == FieldType.MULTIPLE_WITH_META_LANG:
                # reset_index in order to remove the MultiIndex
                df = df.groupby(['index', key]).agg({"value": lambda x: self.inner_sep.join(x)}).reset_index()

            # Now, only one content per key per parent must exist in all cases
            count = df.groupby(['index', key])['index'].transform('count').astype('int')
            if any(count != 1):
                raise Exception(f"All level/{key} pair should give one value (field '{field}')")

            # Turn the data frame into "wide" format
            # Each key value (lang, or type) in its own column
            df = df.pivot(index="index", values="value", columns=key)
            # Clean the multiindex
            arrays = [[field.name] * len(key_values), key_values]
            tuples = list(zip(*arrays))
            index = pd.MultiIndex.from_tuples(tuples, names=["field", key])
            df.columns = index
            # turn NA data into empty strings
            df = df.fillna('')

            res = df
        else:
            raise Exception("I shouldn't be here")

        return res

    def get_parent_id(self, level: LiftLevel) -> List[str]:
        """
    Give the list of the parent id for each level occurrence (for instance, the entry element ID of each sense element).
    :param level: the :class:`LiftLevel`
    :return: list of string
    """
        if not level in self._cached_nodes_by_level:
            self._cached_nodes_by_level[level] = self.dictionary.xpath(LiftVocabulary.LIFT_LEVEL_SPEC[level]["xpath"])
        nodes = self._cached_nodes_by_level[level]
        xpath = "./parent::*/@id"  # TODO LiftVocabulary.LIFT_LEVEL_SPEC[level]["parent_id"]
        values = [node.xpath(xpath) for node in nodes]
        for i, v in enumerate(values):
            if len(v) == 0:
                raise Exception("No id for node: {nodes[i]}")
        return [item for sublist in values for item in sublist]

    def get_id(self, level: LiftLevel) -> List[str]:
        """
    Give the list of the id for each occurrence of the given level (for instance, the ID of each sense element).
    :param level: the :class:`LiftLevel`
    :return: list of string
    """
        if level not in self._cached_nodes_by_level:
            self._cached_nodes_by_level[level] = self.dictionary.xpath(LiftVocabulary.LIFT_LEVEL_SPEC[level]["xpath"])
        nodes = self._cached_nodes_by_level[level]
        xpath = "string(./@id)"
        values = [node.xpath(xpath) for node in nodes]
        for i, v in enumerate(values):
            if v == "":
                raise Exception("No id for node: {nodes[i]}")
        return values

    @staticmethod
    def _create_records(nodes_by_level: List[List[ET.Element]], key_xpath: str, value_xpath: str) -> List[
        Tuple[int, str, str]]:
        # Take care of cases were a node level exists but is empty, such as:
        # <example>
        # </example>
        # This create an empty list in nodes_by_level : [[ET.Element], [], [ET.Element]]
        # And this empty list cannot disapear: it will produce a mismatch between number of level occurrences
        # and number of values
        res = [
            (i, "", "") if isinstance(e, str) else (i, str(e.xpath(key_xpath)), str(e.xpath(value_xpath))) 
            for i, nodes in enumerate(nodes_by_level)
            for e in (nodes if len(nodes) > 0 else "-") #TODO the bug is here
        ]  # each index is not represented anymore
        return res

    @staticmethod
    def _aggregate_values_with_same_key(values: List[List[Dict[str, str]]], key_name: str, key_values: List[str], sep) -> List[List[Dict[str, str]]]:
        res: List[List[Dict[str, str]]] = [None] * len(values)
        for i, nodes in enumerate(values):
            new_node:List[Dict[str, str]] = []
            for l in key_values:
                current_l = ""
                for j, o in enumerate(nodes):
                    if o[key_name] == l:
                        current_l = current_l + sep + o["value"]
                new_node.append({"lang": l, "value": current_l})
            res[i] = new_node
        return res

    @staticmethod
    def _check_uniqueness(pairs_for_nodes_for_nodes: List[List[Dict[str, str]]], key:str, field:LiftField) -> None:
        values_for_nodes_for_nodes: List[List[str]] = [[x[key] for x in sublist] for sublist in pairs_for_nodes_for_nodes]
        is_not_unique_for_nodes_for_nodes: List[bool] = [len(sublist) != len(set(sublist)) for sublist in values_for_nodes_for_nodes]
        index_for_nodes_for_nodes: List[int] = [i for i, v in enumerate(is_not_unique_for_nodes_for_nodes) if v]
        if len(index_for_nodes_for_nodes) > 0:
            raise Exception("Duplicate values for field {field.name} at nodes { check }")

    @staticmethod
    def _test_singleton_inner_list(values: List[List[str]]) -> None:
        is_not_unique = [len(node_list) > 1 for node_list in values]
        if any(is_not_unique):
            index = [i for i, v in enumerate(is_not_unique) if v]
            raise Exception(f"{len(index)} non single value found: {' / '.join(values[index[0]])}")

    def validation(self) -> bool:
        schema = pkgutil.get_data(__name__, "schema/lift.rng")
        if schema == None:
            raise Exception(f"Can't read lift schema (located inside the pylift python package) for validation.")
        schema = cast(bytes, schema) # help mypy with type inference
        schema_string = schema.decode('UTF-8')
        validator = ET.RelaxNG(StringIO(schema_string))
        try:
            validator.assertValid(self.dictionary)
        except Exception as e:
            raise Exception("Lift document is not valid.") from e
            # + dtd.error_log.filter_from_errors()[0])
        return True
