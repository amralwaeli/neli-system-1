from pathlib import Path

import pytest

import app


def test_sample_files_exist():
    assert (Path(app.SAMPLES) / "sample_matlab.m").exists()
    assert (Path(app.SAMPLES) / "sample_python.py").exists()
    assert (Path(app.SAMPLES) / "sample_lean.lean").exists()


@pytest.mark.slow
def test_good_lean_compiles():
    label, out, err = app.run_lean_stage(app.LEAN_GOOD)
    assert label == "Lean accepted"
    assert "error" not in out.lower()
    assert "error" not in err.lower()


@pytest.mark.slow
def test_bad_lean_rejected():
    label, out, err = app.run_lean_stage(app.LEAN_BAD_ATTEMPT)
    assert label == "Lean rejected"
    combined = (out + "\n" + err).lower()
    assert "error" in combined or "placeholder" in combined or "unknown" in combined

