import argparse
import sys
from pylift.lift import LiftDoc, LiftLevel, LiftVocabulary, FieldType, LiftField
from pylift.table import TableSet, AggregatedTable
import os
import pandas as pd
from typing import List
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.FileHandler(os.path.expanduser(Path("~/.pylift.log"))))


def _validate_callback(arg):
    lift = LiftDoc(arg.filename)
    try:
        res = lift.validation()
    except Exception as e:
        print("Dictionary is not valid")
        print(e)
    print("Dictionary is valid")


def _values_callback(arg):
    lift = LiftDoc(arg.filename)
    fieldname = arg.field
    field = _get_field_if_field_exist(fieldname)
    df = lift.get_values(field)
    print(df, file=arg.output)


def _count_callback(arg):
    fieldname = arg.field
    field = _get_field_if_field_exist(fieldname)
    lift = LiftDoc(arg.filename)
    has_subfield = field.field_type == FieldType.UNIQUE_BY_OBJECT_LANG \
                   or field.field_type == FieldType.UNIQUE_BY_META_LANG \
                   or field.field_type == FieldType.UNIQUE_BY_TYPE \
                   or field.field_type == FieldType.MULTIPLE_WITH_META_LANG
    if has_subfield and not arg.subfield:
        _exit_with_error_msg(f"The field '{field.name}' need a --subfield argument")
    elif not has_subfield and arg.subfield:
        _exit_with_error_msg(f"The field '{field.name}' does not have subfield (it can't take a --subfield argument)")
    if not arg.subfield:
        freq = lift.get_frequencies(field, arg.subfield)
    else:
        freq_by_subfield = lift.get_frequencies(field)
        if arg.subfield not in freq_by_subfield:
            _exit_with_error_msg(
                f"The field '{field.name}' have no '{arg.subfield}' subfield. Possible subfield(s): {', '.join(freq_by_subfield.keys())}")
        freq = freq_by_subfield[arg.subfield]
    df = pd.DataFrame.from_dict(freq, orient="index")
    print(df, file=arg.output)


def _get_subfield_callback(arg):
    fieldname = arg.field
    field = _get_field_if_field_exist(fieldname)
    has_subfield = field.field_type == FieldType.UNIQUE_BY_OBJECT_LANG \
                   or field.field_type == FieldType.UNIQUE_BY_META_LANG \
                   or field.field_type == FieldType.UNIQUE_BY_TYPE \
                   or field.field_type == FieldType.MULTIPLE_WITH_META_LANG
    if not has_subfield:
        _exit_with_error_msg(f"The field {field.name} does not accept subfield")
    lift = LiftDoc(arg.filename)
    v = lift.get_values(field)
    subfields = list(v.columns.get_level_values(1))
    for subfield in subfields:
        print(subfield, file=arg.output)


def _convert_callback(arg):
    LOGGER.info("in _convert_callback")
    lift = LiftDoc(arg.filename)
    fieldnames: List[str] = arg.field.split(",")  # list since nargs
    fields = _get_fields_if_fields_exist(fieldnames)
    LOGGER.info(", ".join(fieldnames))
    if arg.aggresep == ",":
        _exit_with_error_msg(
            f"Can't used {arg.aggresep} as aggregation (secondary) separator (it is the value separator in CSV)")
    table = TableSet(lift, fields)
    if arg.output == sys.stdout and arg.output.isatty() and not arg.dir:
        a = AggregatedTable(table, arg.aggregate, inner_sep=arg.aggresep)
        df = a.get_table()
        print(df, file=arg.output)
    else:
        if arg.format == "csv":
            a = AggregatedTable(table, arg.aggregate, inner_sep=arg.aggresep)
            a.to_csv(arg.output)
        elif arg.format == "CLDFWordlist":
            a = AggregatedTable(table, arg.aggregate, inner_sep=arg.aggresep)
            a.to_cldf_Wordlist(arg.dir)
        else:
            _exit_with_error_msg(f"Unknown output type: '{arg.format}'")


def _fields_callback(arg):
    fields_spec = LiftVocabulary.LIFT_FIELD_SPEC
    df = pd.DataFrame.from_dict(fields_spec, orient="index")
    print(df, file=arg.output)


def _summary_callback(arg):
    lift = LiftDoc(arg.filename)

    for level, level_name in zip(
            [LiftLevel.ENTRY, LiftLevel.SENSE, LiftLevel.VARIANT, LiftLevel.EXAMPLE],
            ["entries", "senses", "variants", "examples"]
    ):
        n = lift.get_n(level)
        print(f"{n} {level_name}", file=arg.output)
    olang = lift.get_object_languages()
    mlang = lift.get_meta_languages()
    print(f"Object languages: {', '.join(olang)}")
    print(f"Meta languages: {', '.join(mlang)}")


def _exit_with_error_msg(msg):
    LOGGER.warning(msg)
    print(msg)
    sys.exit()


def _get_fields_if_fields_exist(fieldnames) -> List[LiftField]:
    if not set(fieldnames).issubset(LiftVocabulary.LIFT_FIELD_SPEC.keys()):
        _exit_with_error_msg('Unknown field(s): %r' % sorted(set(fieldnames).difference(LiftVocabulary.LIFT_FIELD_SPEC.keys())))
    return [LiftVocabulary.LIFT_FIELD_SPEC[fieldname] for fieldname in fieldnames]


def _get_field_if_field_exist(fieldname) -> LiftField:
    if not fieldname in LiftVocabulary.LIFT_FIELD_SPEC:
        _exit_with_error_msg("Unknown field: '{fieldname}'")
    return LiftVocabulary.LIFT_FIELD_SPEC[fieldname]


def liftlex():
    # Main level
    parser = argparse.ArgumentParser(description='Utilities for LIFT (lexicon interchange format) lexicon.')
    parser.add_argument('--verbose', '-v', help='output detailled information', required=False, action='store_true')
    parser.add_argument('--output', '-o', help='output file (or standard output if not specified)', nargs="?",
                        default=sys.stdout, type=argparse.FileType("w"))
    # TODO : doc argparse : defaut sys

    # 1/
    command_subparser = parser.add_subparsers(title="subcommand", description="one valid subcommand",
                                              help='subcommand: the main action to run. See `subcommand -h` for more '
                                                   'info',
                                              required=True)

    # summary subcommand
    summary = command_subparser.add_parser('summary', help='Print summary about the lexicon')
    summary.set_defaults(func=_summary_callback)

    # values of given field subcommand
    v = command_subparser.add_parser('values', help='List the values for the given field')
    v.add_argument('--field', '-f', help='select the field to be listed', default="form",
                   choices=LiftVocabulary.LIFT_FIELD_SPEC.keys(), required=False, type=str)
    v.set_defaults(func=_values_callback)

    # _get_subfield_callback
    v = command_subparser.add_parser('subfield', help='List the subfields for the given field')
    v.add_argument('--field', '-f', help='select the field to be listed', default="form",
                   choices=LiftVocabulary.LIFT_FIELD_SPEC.keys(), required=False, type=str)
    v.set_defaults(func=_get_subfield_callback)

    # frequency list of given field subcommand
    count = command_subparser.add_parser('count', help='compute frequencies for the given field')
    count.add_argument('--field', '-f', help='select the field to be tabulated', default="category",
                       choices=LiftVocabulary.LIFT_FIELD_SPEC.keys(), required=False, type=str)
    count.add_argument('--subfield', '-s', help='Subfield (lang, or type) or the field, if relevant', default="",
                       required=False, type=str)
    count.set_defaults(func=_count_callback)

    # convert subcommand
    convert = command_subparser.add_parser('convert', help='Convert toward other formats')
    convert.add_argument('--field', '-f', help='commat-separated list of the field(s) to be used', required=True,
                         type=str)  # , nargs="+", action="extend", choices=LiftVocabulary.LIFT_FIELD_SPEC.keys()
    convert.add_argument('--format', '-a', help='select the output format', default="CLDFWordlist",
                         choices=["csv", "CLDFWordlist", "CLDFDictionary"], required=True, type=str)
    convert.add_argument('--aggregate', '-g', help='aggregate rows on same object', action='store_true')
    convert.add_argument('--aggresep', '-p', help='the character for separating aggregated values', default=";",
                         required=False, type=str)
    convert.add_argument('--dir', '-d', help='the directory for CLDFWordlist conversion', default=".",
                         required=False, type=str)
    convert.set_defaults(func=_convert_callback)

    # validate subcommand
    validate = command_subparser.add_parser('validate', help='validation against LIFT schema')
    validate.set_defaults(func=_validate_callback)

    parser.add_argument('filename', type=str, help='Lift filename')

    # # 2/ Command that do not need a lift file no_lift_arg_command_subparser = parser.add_subparsers(title="'fields'
    # subcommand", description="one valid subcommand", help='subcommand: the main action to run. See `subcommand -h`
    # for more info', required=True) # list field subcommand
    fields = command_subparser.add_parser('fields',
                                          help='List the available fields in the dictionary that can be refered to in '
                                               'other commands')
    fields.set_defaults(func=_fields_callback)

    if len(sys.argv) <= 1:
        sys.argv.append('-h')
    if len(sys.argv) == 2 and sys.argv[1] == "convert":
        sys.argv.append('-h')
    argument = parser.parse_args()

    for arg in vars(argument):
        LOGGER.info(f"Argument: {arg}, / {getattr(argument, arg)}")

    if not os.access(argument.filename, os.R_OK):
        raise _exit_with_error_msg(f"{argument.filename} is not readable")
    argument.func(argument)
