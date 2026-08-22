"""SWaT-style 6-stage surrogate plant model. Pure, deterministic, in-memory.

NO shell, NO subprocess, NO network, NO file I/O, NO real hardware (R1/R4).
State is a plain dict; every action is a named Python function operating on
that dict and returning a telemetry delta.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def initial_state() -> dict:
    return {
        "stage1": {"pumps": {"P-101": {"on": False, "speed_pct": 0.0}},
                   "tank": {"T-101": {"level_pct": 50.0}}},
        "stage2": {"valves": {"MV-201": {"open": True}}},
        "stage3": {"tanks": {"T-301": {"level_pct": 50.0}}},
        "stage4": {"pumps": {"P-401": {"on": False, "speed_pct": 0.0}}},
        "stage5": {"valves": {"MV-501": {"open": True}}},
        "stage6": {"tanks": {"T-601": {"level_pct": 50.0}}},
        "flows": {"FIT-101": 0.0, "FIT-201": 2.4, "FIT-401": 0.0, "FIT-601": 2.1},
        "setpoints": {"T-101": 50.0, "T-301": 50.0, "T-501": 50.0},
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class PlantModel:
    state: dict = field(default_factory=initial_state)

    # ---- read actions ------------------------------------------------------
    def snapshot_plant_state(self, target: str, params: dict) -> dict:
        return {"snapshot": self.state, "label": "SIMULATED"}

    def query_tank_level(self, target: str, params: dict) -> dict:
        for stage in self.state.values():
            tanks = stage.get("tank") or stage.get("tanks") or {}
            if target in tanks:
                return {"sensor": target, "level_pct": tanks[target]["level_pct"],
                        "label": "SIMULATED"}
        raise KeyError(f"unknown tank {target}")

    # ---- control actions ----------------------------------------------------
    def set_pump_speed(self, target: str, params: dict) -> dict:
        speed = float(params["speed_pct"])
        pump = None
        for stage in self.state.values():
            pumps = stage.get("pumps") or {}
            if target in pumps:
                pump = pumps[target]
        if pump is None:
            raise KeyError(f"unknown pump {target}")
        before = dict(pump)
        pump["speed_pct"] = _clamp(speed, 0.0, 100.0)
        pump["on"] = pump["speed_pct"] > 0.0
        flow_key = "FIT-101" if target == "P-101" else "FIT-401"
        self.state["flows"][flow_key] = round(pump["speed_pct"] / 100.0 * 12.5, 3)
        return {"action": "set_pump_speed", "target": target,
                "before": before, "after": dict(pump), "label": "SIMULATED"}

    def open_valve(self, target: str, params: dict) -> dict:
        return self._set_valve(target, True)

    def close_valve(self, target: str, params: dict) -> dict:
        return self._set_valve(target, False)

    def _set_valve(self, target: str, open_: bool) -> dict:
        for stage in self.state.values():
            valves = stage.get("valves") or {}
            if target in valves:
                before = dict(valves[target])
                valves[target]["open"] = open_
                return {"action": "open_valve" if open_ else "close_valve",
                        "target": target, "before": before,
                        "after": dict(valves[target]), "label": "SIMULATED"}
        raise KeyError(f"unknown valve {target}")

    # ---- write actions -------------------------------------------------------
    def set_tank_setpoint(self, target: str, params: dict) -> dict:
        level = _clamp(float(params["level_pct"]), 0.0, 100.0)
        before = self.state["setpoints"].get(target)
        if before is None:
            raise KeyError(f"unknown setpoint {target}")
        self.state["setpoints"][target] = level
        return {"action": "set_tank_setpoint", "target": target,
                "before": before, "after": level, "label": "SIMULATED"}

    def update_alarm_threshold(self, target: str, params: dict) -> dict:
        return {"action": "update_alarm_threshold", "target": str(params["sensor"]),
                "after": float(params["threshold"]), "label": "SIMULATED"}

    # ---- dispatch -------------------------------------------------------------
    def apply(self, action: str, target: str, params: dict) -> dict:
        fn = getattr(self, action, None)
        if fn is None or not callable(fn):
            raise ValueError(f"sandbox_unknown_action:{action}")
        return fn(target, params)  # type: ignore[operator]
