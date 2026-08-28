"""Every experiment in the matrix has a committed config YAML (EVAL-07 / R22)."""
from __future__ import annotations

from pathlib import Path

CONFIGS_DIR = Path("configs/experiments")

# All experiment IDs that should have a committed config.
# EXP-03..07 are agent experiments; EXP-01/02 are detector; EXP-08/09 are
# injection/bypass; STRESS-ROB is the stress-sweep + channel-reduction arm.
EXPECTED_EXPS = {
    "EXP-01", "EXP-02", "EXP-03", "EXP-04",
    "EXP-05", "EXP-06", "EXP-07", "EXP-08",
    "EXP-09", "STRESS-ROB",
}


def test_all_experiments_have_config():
    files = list(CONFIGS_DIR.glob("*.yaml"))
    stems = {f.stem for f in files}
    missing = []
    for exp in EXPECTED_EXPS:
        if exp == "STRESS-ROB":
            ok = exp in stems
        else:
            ok = any(s == exp or s.startswith(exp + "_") for s in stems)
        if not ok:
            missing.append(exp)
    assert not missing, f"experiments missing committed configs: {missing}"


def test_every_config_is_parseable():
    import yaml

    for f in sorted(CONFIGS_DIR.glob("*.yaml")):
        raw = f.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        assert data, f"{f.name} is empty"
        assert "experiment" in data, f"{f.name} missing experiment field"


def test_experiment_id_matches_filename():
    configs_dir = CONFIGS_DIR
    for f in configs_dir.glob("EXP-*.yaml"):
        import yaml

        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        exp_id = data.get("experiment", "")
        assert exp_id in f.stem, f"{f.name}: experiment={exp_id} doesn't match filename"