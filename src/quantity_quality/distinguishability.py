from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from .model import QuantityQualityRecord


DISTINGUISHABILITY_SCHEMA_VERSION = "1.0"
_ZERO_TOLERANCE = 1e-12


@dataclass(frozen=True)
class DistinguishabilityAssessment:
    """Explain the state difference represented by an Exergy Factor.

    Distinguishability is not an additional multiplier. The Exergy Factor already
    quantifies the work-bearing difference between a stream and its declared
    reference environment or service boundary.
    """

    status: str
    basis: str
    evidence: str
    exergy_factor: float
    source_state: Mapping[str, object] = field(default_factory=dict)
    reference_state: Mapping[str, object] = field(default_factory=dict)
    difference: Mapping[str, object] = field(default_factory=dict)

    @property
    def distinguishable(self) -> bool:
        return self.status == "distinguishable"

    def as_dict(self) -> dict:
        payload = {
            "schema_version": DISTINGUISHABILITY_SCHEMA_VERSION,
            "status": self.status,
            "distinguishable": self.distinguishable,
            "basis": self.basis,
            "evidence": self.evidence,
            "exergy_factor": self.exergy_factor,
            "factor_role": (
                "fx quantifies the work-bearing difference; no separate "
                "distinguishability multiplier is applied"
            ),
        }
        if self.source_state:
            payload["source_state"] = dict(self.source_state)
        if self.reference_state:
            payload["reference_state"] = dict(self.reference_state)
        if self.difference:
            payload["difference"] = dict(self.difference)
        return payload


def assess_distinguishability(record: QuantityQualityRecord) -> DistinguishabilityAssessment:
    """Return the declared or calculated disequilibrium behind one record."""

    unit = record.unit.lower()
    stream_type = (record.stream_type or "").lower()
    status = (
        "indistinguishable" if abs(record.exergy_factor) <= _ZERO_TOLERANCE else "distinguishable"
    )

    if record.method in {"solar", "radiation"}:
        reference_state = {"temperature_c": record.sink_c} if record.sink_c is not None else {}
        source_state = {"radiation_model": record.metadata.get("radiation_model", "solar")}
        if record.source_c is not None:
            source_state["source_temperature_c"] = record.source_c
        return DistinguishabilityAssessment(
            status=status,
            basis="radiative_state_difference",
            evidence="computed_reference_model",
            exergy_factor=record.exergy_factor,
            source_state=source_state,
            reference_state=reference_state,
        )

    if record.source_c is not None and record.return_c is not None and record.sink_c is not None:
        return DistinguishabilityAssessment(
            status=status,
            basis="sensible_temperature_path",
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={
                "supply_temperature_c": record.source_c,
                "return_temperature_c": record.return_c,
            },
            reference_state={"temperature_c": record.sink_c},
            difference={
                "supply_to_reference_k": record.source_c - record.sink_c,
                "return_to_reference_k": record.return_c - record.sink_c,
            },
        )

    if record.source_c is not None and record.sink_c is not None:
        return DistinguishabilityAssessment(
            status=status,
            basis="temperature_gradient",
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={"temperature_c": record.source_c},
            reference_state={"temperature_c": record.sink_c},
            difference={"temperature_k": record.source_c - record.sink_c},
        )

    if record.cold_service_c is not None and record.ambient_sink_c is not None:
        return DistinguishabilityAssessment(
            status=status,
            basis="cooling_temperature_gradient",
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={"cold_service_temperature_c": record.cold_service_c},
            reference_state={"ambient_temperature_c": record.ambient_sink_c},
            difference={
                "ambient_above_cold_service_k": (record.ambient_sink_c - record.cold_service_c)
            },
        )

    if record.method in {"fluid", "humid_air"}:
        return DistinguishabilityAssessment(
            status=status,
            basis=(
                "humid_air_temperature_pressure_composition_difference"
                if record.method == "humid_air"
                else "fluid_state_difference"
            ),
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={
                key: value
                for key, value in record.metadata.items()
                if key
                in {
                    "fluid",
                    "temperature_k",
                    "pressure_pa",
                    "enthalpy_kj_kg",
                    "entropy_kj_kg_k",
                }
            },
            reference_state={"reference": record.reference},
        )

    if record.method == "plasma":
        return DistinguishabilityAssessment(
            status=status,
            basis="plasma_temperature_composition_motion_and_field_difference",
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={
                "model": record.metadata.get("model", "declared plasma state"),
                "species": record.metadata.get("species", []),
                "field_model": record.metadata.get("field_model"),
            },
            reference_state={"reference": record.reference},
        )

    if record.method == "electromagnetic":
        return DistinguishabilityAssessment(
            status=status,
            basis="electromagnetic_field_or_flux_difference",
            evidence="computed_state_difference",
            exergy_factor=record.exergy_factor,
            source_state={"field_model": record.metadata.get("field_model")},
            reference_state={"reference": record.reference},
        )

    if record.method == "electricity" or stream_type == "electricity" or unit.endswith("_e"):
        return DistinguishabilityAssessment(
            status=status,
            basis="electrical_work",
            evidence="carrier_convention",
            exergy_factor=record.exergy_factor,
            source_state={"carrier": "electricity"},
            reference_state={"boundary": record.boundary or "delivery boundary"},
        )

    if (
        record.method in {"fuel", "chemical"}
        or stream_type == "fuel"
        or record.fuel
        or record.energy_basis
        or "_hhv" in unit
        or "_lhv" in unit
    ):
        return DistinguishabilityAssessment(
            status=status,
            basis="chemical_composition_difference",
            evidence=("reference_factor" if record.reference_id else "declared_chemical_basis"),
            exergy_factor=record.exergy_factor,
            source_state={
                "fuel": record.fuel or record.label or "declared chemical carrier",
                "energy_basis": record.energy_basis or "declared basis",
            },
            reference_state={"environment": record.reference or "declared chemical environment"},
        )

    is_mechanical = record.method == "mechanical" or unit.endswith(("_m", "_mech"))
    if record.method in {"fission", "nuclear"} or is_mechanical:
        carrier = "mechanical" if is_mechanical else record.method
        return DistinguishabilityAssessment(
            status=status,
            basis=f"{carrier}_work_potential",
            evidence="declared_carrier_model",
            exergy_factor=record.exergy_factor,
            source_state={"carrier": carrier},
            reference_state={"boundary": record.boundary or "declared boundary"},
        )

    return DistinguishabilityAssessment(
        status=status,
        basis="declared_work_potential_difference",
        evidence="reference_factor" if record.reference_id else "declared_factor",
        exergy_factor=record.exergy_factor,
        source_state={"label": record.label or "declared energy stream"},
        reference_state={"reference": record.reference or "not specified"},
    )


def distinguishability_capabilities() -> dict:
    """Describe the non-duplicative role of distinguishability in the model."""

    return {
        "schema_version": DISTINGUISHABILITY_SCHEMA_VERSION,
        "definition": (
            "A stream is thermodynamically distinguishable when its state differs from a "
            "declared environment or service boundary in a way that can support work."
        ),
        "accounting_rule": (
            "Distinguishability is the physical basis of exergy and is exposed as evidence, "
            "not multiplied into fx as a second factor."
        ),
        "statuses": ["distinguishable", "indistinguishable"],
        "evidence_levels": [
            "computed_state_difference",
            "computed_reference_model",
            "carrier_convention",
            "reference_factor",
            "declared_chemical_basis",
            "declared_carrier_model",
            "declared_factor",
        ],
    }
