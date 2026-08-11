from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Optional, Union

from .core import Number, thermal_exergy_factor_c, weighted_exergy_factor
from .model import QuantityQualityRecord


@dataclass(frozen=True)
class ThermalIntervalInput:
    """Minimal F3 interval input for a thermal stream."""

    quantity: float
    source_c: float
    sink_c: float
    unit: str = "MWh_th"
    timestamp: Optional[str] = None
    stream_id: Optional[str] = None

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class F3ThermalSummary:
    """Dynamic interval Exergy Factor summary."""

    intervals: int
    total_quantity: float
    weighted_fx: float
    unit: str
    fixed_sink_c: Optional[float] = None
    weighted_fixed_sink_fx: Optional[float] = None

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


def thermal_interval(
    quantity: Number,
    *,
    source_c: Number,
    sink_c: Number,
    unit: str = "MWh_th",
    timestamp: Optional[str] = None,
    interval: Optional[str] = None,
    stream_id: Optional[str] = None,
    boundary: str = "thermal interval",
    label: Optional[str] = None,
) -> QuantityQualityRecord:
    """Create an F3 thermal interval record from synchronized telemetry."""

    source = float(source_c)
    sink = float(sink_c)
    factor = thermal_exergy_factor_c(source, sink)
    metadata = {
        "interval": interval or "",
        "timestamp": timestamp or "",
        "stream_id": stream_id or "",
        "synchronization": "source temperature, sink temperature, and quantity are assumed synchronized",
    }
    return QuantityQualityRecord(
        quantity=float(quantity),
        unit=unit,
        exergy_factor=factor,
        reference=f"T0 = {sink:g} C",
        boundary=boundary,
        basis=f"F3 dynamic interval Carnot factor, source={source:g} C, sink={sink:g} C",
        method="thermal_interval",
        label=label or stream_id,
        source_c=source,
        sink_c=sink,
        tier="F3",
        metadata={key: value for key, value in metadata.items() if value not in (None, "")},
    )


def f3_thermal_summary(
    intervals: Iterable[Union[Mapping[str, object], ThermalIntervalInput]],
    *,
    unit: str = "MWh_th",
    fixed_sink_c: Optional[float] = None,
) -> F3ThermalSummary:
    """Compute the F3 weighted-average Exergy Factor for thermal intervals."""

    dynamic_records = []
    fixed_records = []
    total_quantity = 0.0
    count = 0
    for interval in intervals:
        data = interval.as_dict() if isinstance(interval, ThermalIntervalInput) else dict(interval)
        quantity = float(data["quantity"])
        source_c = float(data["source_c"])
        sink_c = float(data["sink_c"])
        fx_dynamic = thermal_exergy_factor_c(source_c, sink_c)
        dynamic_records.append((quantity, fx_dynamic))
        if fixed_sink_c is not None:
            fixed_records.append((quantity, thermal_exergy_factor_c(source_c, fixed_sink_c)))
        total_quantity += quantity
        count += 1

    weighted_fx = weighted_exergy_factor(dynamic_records)
    weighted_fixed = weighted_exergy_factor(fixed_records) if fixed_records else None
    return F3ThermalSummary(
        intervals=count,
        total_quantity=total_quantity,
        weighted_fx=weighted_fx,
        unit=unit,
        fixed_sink_c=fixed_sink_c,
        weighted_fixed_sink_fx=weighted_fixed,
    )
