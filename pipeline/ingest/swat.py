"""SWaT ingestion (DATA-01). Builds one contiguous, chronologically ordered
slice of the testbed and writes the frozen feature-manifest layout.

The source used here is the SWaT water-treatment testbed export (51 channels,
1 Hz, 28 Dec 2015 - 2 Jan 2016) as republished on Kaggle; it is a mirror, not
the original iTrust distribution, so the slice hash is pinned in `datasets`.

Four channels are kept, matching configs/features.yaml: FIT101 (feed flow),
LIT101 (tank level), P101 (pump state, renamed P101_STATE) and AIT502
(analyser). MV101 is excluded because 71% of its normal-run values are absent.
Slice sizes are chosen so the held-out test range contains BOTH normal and
attack rows: with the attack run chronologically last, a test range drawn from
the tail would otherwise be all-attack and precision/FPR would be meaningless.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SENSORS = {"FIT101": "FIT101", "LIT101": "LIT101", "P101": "P101_STATE",
           "AIT502": "AIT502"}
TS_FMT = "%d/%m/%Y %I:%M:%S %p"


def _load(path: str | Path, label: int) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=lambda c: c.strip() in SENSORS or
                     c.strip() in ("Timestamp", "Normal/Attack"))
    df.columns = [c.strip() for c in df.columns]
    keep = {"Timestamp": "timestamp"}
    keep.update({src: dst for src, dst in SENSORS.items() if src in df.columns})
    out = df.rename(columns=keep)[list(keep.values())].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"].str.strip(),
                                      format=TS_FMT)
    out["label"] = label
    return (out.sort_values("timestamp")
               .drop_duplicates("timestamp", keep="first")
               .reset_index(drop=True))


def build_slice(normal_path: str | Path, attack_path: str | Path,
                out_path: str | Path, normal_rows: int = 24000,
                attack_rows: int = 5600,
                normal_take: str = "head",
                normal_until: str | None = None) -> dict:
    """Contiguous tail of the normal session + contiguous head of the attack
    session, concatenated in that order. The two SWaT recording sessions
    overlap in wall-clock time, so they are NOT merged by timestamp: each block
    is internally monotonic and no row is shuffled within a block."""
    normal = _load(normal_path, 0)
    attack = _load(attack_path, 1)
    for name, block in (("normal", normal), ("attack", attack)):
        if block["timestamp"].is_monotonic_increasing is False:
            raise ValueError(f"{name}_session_not_monotonic")
    if normal_until:
        normal = normal[normal["timestamp"] <= pd.Timestamp(normal_until)]
    n_take = min(normal_rows, len(normal))
    a_take = min(attack_rows, len(attack))
    if normal_until:
        normal_block = normal.iloc[-n_take:]
    else:
        normal_block = (normal.iloc[:n_take] if normal_take == "head"
                        else normal.iloc[-n_take:])
    df = pd.concat([normal_block, attack.iloc[:a_take]], ignore_index=True)
    missing = df[list(SENSORS.values())].isna().mean().max()
    df = df.ffill().bfill().reset_index(drop=True)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return {"rows": len(df), "normal": int((df["label"] == 0).sum()),
            "attack": int((df["label"] == 1).sum()),
            "attack_starts_at_row": int(n_take),
            "sensors": [c for c in df.columns if c not in ("timestamp", "label")],
            "worst_missing_frac_before_fill": round(float(missing), 4),
            "normal_span": (normal_block["timestamp"].iloc[0],
                            normal_block["timestamp"].iloc[-1]),
            "attack_span": (attack["timestamp"].iloc[0],
                            attack["timestamp"].iloc[a_take - 1]),
            "out": str(out)}


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Build the SWaT slice CSV")
    ap.add_argument("--normal", default="data/raw/swat/normal.csv")
    ap.add_argument("--attack", default="data/raw/swat/attack.csv")
    ap.add_argument("--out", default="data/raw/swat/swat_slice.csv")
    ap.add_argument("--normal-rows", type=int, default=24000)
    ap.add_argument("--attack-rows", type=int, default=5600)
    ap.add_argument("--normal-take", default="head", choices=("head", "tail"))
    ap.add_argument("--normal-until", default=None,
                    help="take the N normal rows ending at this timestamp")
    a = ap.parse_args()
    print(build_slice(a.normal, a.attack, a.out, a.normal_rows, a.attack_rows,
                      a.normal_take, a.normal_until))


if __name__ == "__main__":
    main()
