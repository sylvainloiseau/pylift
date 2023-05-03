from cli import liftlex
import sys
import logging

LOGGER = logging.getLogger(__name__)


def _get_subfield_callback(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "subfield", "--field=form", "tiny.lift"], capsys, caplog, tmp_path)
    assert "tww" in out


def test_summary(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "summary", "tests/data/FlexLiftExport.lift"], capsys, caplog, tmp_path)
    assert "182 entries" in out


def test_fields(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "fields", "tests/data/FlexLiftExport.lift"], capsys, caplog, tmp_path)
    assert "form" in out


def test_count(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "count", "--field=morphtype", "tests/data/FlexLiftExport.lift"], capsys, caplog,
                   tmp_path)
    assert "stem" in out


def test_values(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "values", "--field=form", "tests/data/tiny.lift"], capsys, caplog, tmp_path)
    assert "hei" in out


def test_convert(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "convert", "--field=ID,form,category", "--format=csv", "tests/data/FlexLiftExport.lift"],
                   capsys, caplog, tmp_path)
    assert "ID" in out


def test_convert_tiny(capsys, caplog, tmp_path):  #
    out = _run_cli(["liftlex", "convert", "--field=ID,form,category", "--format=csv", "tests/data/tiny.lift"], capsys,
                   caplog, tmp_path)
    assert "ID" in out


def test_aggregate(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "convert", "--field=ID,form,gloss", "-g", "--format=csv", "tests/data/tiny.lift"],
                   capsys, caplog, tmp_path)
    assert "road;skin" in out


def test_aggregate_not(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "convert", "--field=ID,gloss,form", "--format=csv", "tests/data/tiny.lift"], capsys,
                   caplog, tmp_path)
    assert ",skin," in out


def test_validate_callback(capsys, caplog, tmp_path):
    out = _run_cli(["liftlex", "validate", "tests/data/FlexLiftExport.lift"], capsys, caplog, tmp_path)
    assert "Dictionary is valid" in out


def _run_cli(args, capsys, caplog, tmp_path):
    try:
        sys.argv = args
        liftlex()
    except SystemExit:
        captured = capsys.readouterr()
        print(captured.err)
        assert False
    captured = capsys.readouterr()
    return captured.out
