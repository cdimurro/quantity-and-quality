from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from .core import (
    EnergyReport,
    ReferenceContext,
    accessible_exergy,
    exergy_unit,
    format_energy_notation,
)
from .registry import CARRIER_REGISTRY_VERSION
from .tiers import conformance_issues, infer_fidelity_tier, normalize_tier
from .units import convert_energy, convert_power, is_energy_unit, is_non_energy_unit, is_power_unit


@dataclass(frozen=True)
class QuantityQualityRecord:
    """A cleaned Quantity + Quality reporting record.

    Users can start with only `quantity`, `unit`, and `fx`. More context can be
    attached when records need to be interpreted, verified, compared, or audited.
    """

    quantity: float
    unit: str
    exergy_factor: float
    reference: str = ""
    boundary: str = ""
    basis: str = ""
    method: str = "supplied"
    tier: str = ""
    label: Optional[str] = None
    source_c: Optional[float] = None
    return_c: Optional[float] = None
    sink_c: Optional[float] = None
    cold_service_c: Optional[float] = None
    ambient_sink_c: Optional[float] = None
    fuel: Optional[str] = None
    energy_basis: Optional[str] = None
    reference_id: Optional[str] = None
    method_id: Optional[str] = None
    stream_type: Optional[str] = None
    quantity_method_id: Optional[str] = None
    calculation_inputs: Mapping[str, object] = field(default_factory=dict)
    carrier_registry_version: str = CARRIER_REGISTRY_VERSION
    uncertainty: Optional[object] = None
    data_quality_flag: Optional[str] = None
    assumptions: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if is_non_energy_unit(self.unit):
            raise ValueError(
                f"{self.unit} measures volume or mass, not energy; convert it with a "
                "declared heating value before applying an Exergy Factor"
            )
        # Reuse EnergyReport validation without forcing the old report model on users.
        EnergyReport(
            quantity=self.quantity,
            unit=self.unit,
            exergy_factor=self.exergy_factor,
            context=ReferenceContext(
                reference=self.reference or "declared by reporter",
                boundary=self.boundary or "declared reporting boundary",
                operating_basis=self.basis or "provided Exergy Factor",
            ),
            label=self.label,
        )
        if self.tier:
            normalize_tier(self.tier)

    @property
    def fx(self) -> float:
        return self.exergy_factor

    @property
    def notation(self) -> str:
        return format_energy_notation(self.quantity, self.unit, self.exergy_factor)

    @property
    def full_notation(self) -> str:
        bracket = self._context_bracket()
        if not bracket:
            return self.notation
        return f"{self.notation} {bracket}"

    @property
    def fidelity_tier(self) -> str:
        if self.tier:
            return normalize_tier(self.tier)
        return infer_fidelity_tier(self._tier_payload())

    @property
    def accessible_exergy(self) -> float:
        return accessible_exergy(self.quantity, self.exergy_factor)

    @property
    def accessible_exergy_unit(self) -> str:
        return exergy_unit(self.unit)

    @property
    def accessible_exergy_mwh(self) -> Optional[float]:
        if not is_energy_unit(self.unit):
            return None
        return convert_energy(self.accessible_exergy, self.accessible_exergy_unit, "MWh")

    @property
    def accessible_exergy_mw(self) -> Optional[float]:
        if not is_power_unit(self.unit):
            return None
        return convert_power(self.accessible_exergy, self.accessible_exergy_unit, "MW")

    @property
    def distinguishability(self) -> dict:
        """Describe the state difference already quantified by this record's fx."""

        from .distinguishability import assess_distinguishability

        return assess_distinguishability(self).as_dict()

    @property
    def capabilities(self) -> Tuple[str, ...]:
        capabilities = ["notation", "accessible_exergy", "distinguishability_assessment"]
        if is_energy_unit(self.unit):
            capabilities.append("normalized_mwh_ex")
        if is_power_unit(self.unit):
            capabilities.append("normalized_mw_ex")
        if self.reference or self.boundary or self.basis:
            capabilities.append("declared_context")
        if self._is_self_verifying:
            capabilities.append("self_verifying")
        if self.reference_id:
            capabilities.append("reference_lookup")
        if self.stream_type:
            capabilities.append("stream_calculation")
        if self.method in {
            "thermal",
            "cooling",
            "solar",
            "radiation",
            "chemical",
            "fuel",
            "mechanical",
            "electromagnetic",
            "fluid",
            "humid_air",
            "plasma",
            "separation",
            "fission",
            "nuclear",
            "dissipation",
        }:
            capabilities.append(f"{self.method}_method")
        capabilities.append(f"tier_{self.fidelity_tier.lower()}")
        return tuple(capabilities)

    @property
    def missing_context(self) -> Tuple[str, ...]:
        missing = []
        if not self.reference:
            missing.append("reference")
        if not self.boundary:
            missing.append("boundary")
        if not self.basis:
            missing.append("basis")
        unit_lower = self.unit.lower()
        if "_th" in unit_lower and self.method not in {"fluid", "dissipation"}:
            if self.source_c is None:
                missing.append("source_c")
            if self.sink_c is None:
                missing.append("sink_c")
            if self.method_identifier == "thermal.sensible.integrated.v1" and self.return_c is None:
                missing.append("return_c")
        if "cooling" in unit_lower:
            if self.cold_service_c is None:
                missing.append("cold_service_c")
            if self.ambient_sink_c is None:
                missing.append("ambient_sink_c")
        if self.method in {"fuel", "chemical"} or "_hhv" in unit_lower or "_lhv" in unit_lower:
            if not self.energy_basis:
                missing.append("energy_basis")
        return tuple(dict.fromkeys(missing))

    @property
    def readiness(self) -> dict:
        return {
            "tier": self.fidelity_tier,
            "capabilities": list(self.capabilities),
            "missing_context": list(self.missing_context),
            "conformance_issues": list(self.conformance_issues),
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
        }

    @property
    def conformance_issues(self) -> Tuple[str, ...]:
        return conformance_issues(self._tier_payload(), tier=self.fidelity_tier)

    @property
    def ok(self) -> bool:
        return True

    @property
    def needs_attention(self) -> bool:
        return bool(self.warnings or self.missing_context or self.conformance_issues)

    def format(self, *, full: bool = False) -> str:
        return self.full_notation if full else self.notation

    def as_dict(self) -> dict:
        payload = {
            "quantity": self.quantity,
            "unit": self.unit,
            "exergy_factor": self.exergy_factor,
            "fx": self.exergy_factor,
            "tier": self.fidelity_tier,
            "fidelity_tier": self.fidelity_tier,
            "notation": self.notation,
            "full_notation": self.full_notation,
            "accessible_exergy": self.accessible_exergy,
            "accessible_exergy_unit": self.accessible_exergy_unit,
            "distinguishability": self.distinguishability,
            "capabilities": list(self.capabilities),
            "missing_context": list(self.missing_context),
            "readiness": self.readiness,
            "needs_attention": self.needs_attention,
            "method": self.method,
            "method_id": self.method_identifier,
            "type": "energy",
            "carrier_registry_version": self.carrier_registry_version,
            "reference": self.reference,
            "boundary": self.boundary,
            "basis": self.basis,
            "label": self.label,
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
        }
        optional_fields = {
            "source_c": self.source_c,
            "return_c": self.return_c,
            "sink_c": self.sink_c,
            "cold_service_c": self.cold_service_c,
            "ambient_sink_c": self.ambient_sink_c,
            "fuel": self.fuel,
            "energy_basis": self.energy_basis,
            "reference_id": self.reference_id,
            "stream_type": self.stream_type,
            "quantity_method_id": self.quantity_method_id,
            "uncertainty": self.uncertainty,
            "data_quality_flag": self.data_quality_flag,
            "accessible_exergy_mwh": self.accessible_exergy_mwh,
            "accessible_exergy_mw": self.accessible_exergy_mw,
        }
        payload.update({key: value for key, value in optional_fields.items() if value is not None})
        metadata = {key: value for key, value in self.metadata.items() if value not in (None, "")}
        if self.calculation_inputs:
            payload["calculation_inputs"] = dict(self.calculation_inputs)
        if metadata:
            payload["metadata"] = metadata
        return {key: value for key, value in payload.items() if value not in (None, "")}

    def to_energy_report(self) -> EnergyReport:
        return EnergyReport(
            quantity=self.quantity,
            unit=self.unit,
            exergy_factor=self.exergy_factor,
            label=self.label,
            context=ReferenceContext(
                reference=self.reference or "declared by reporter",
                boundary=self.boundary or "declared reporting boundary",
                operating_basis=self.basis or "provided Exergy Factor",
                notes="; ".join([*self.assumptions, *self.warnings]) or None,
            ),
        )

    @property
    def _is_self_verifying(self) -> bool:
        if self.source_c is not None and self.sink_c is not None:
            return True
        if self.cold_service_c is not None and self.ambient_sink_c is not None:
            return True
        if self.method == "solar" and self.sink_c is not None:
            return True
        return False

    @property
    def method_identifier(self) -> str:
        """Return a stable calculation identifier for machine-readable records."""

        if self.method_id:
            return self.method_id
        if self.reference_id:
            return f"reference.lookup.{self.reference_id}"
        if self.method == "thermal" and self.return_c is not None:
            return "thermal.sensible.integrated.v1"
        return {
            "thermal": "thermal.carnot.constant_temperature.v1",
            "cooling": "cooling.minimum_work.constant_temperature.v1",
            "solar": "solar.petela.v1",
            "chemical": "chemical.ratio.declared_basis.v1",
            "fuel": "fuel.reference_factor.v1",
            "electricity": "electricity.work_equivalent.v1",
            "mechanical": "mechanical.work_equivalent.v1",
            "fluid": "fluid.physical_exergy.declared_properties.v1",
            "humid_air": "humid_air.wepfer.total_flow_exergy.v1",
            "radiation": "radiation.declared_model.v1",
            "separation": "separation.minimum_work.v1",
            "dissipation": "dissipation.to_heat.v1",
            "fission": "fission.declared_factor.v1",
            "supplied": "factor.supplied.v1",
        }.get(self.method, f"{self.method}.v1")

    def _tier_payload(self) -> dict:
        payload = {
            "quantity": self.quantity,
            "unit": self.unit,
            "fx": self.exergy_factor,
            "exergy_factor": self.exergy_factor,
            "reference": self.reference,
            "boundary": self.boundary,
            "basis": self.basis,
            "method": self.method,
            "method_id": self.method_identifier,
            "source_c": self.source_c,
            "return_c": self.return_c,
            "sink_c": self.sink_c,
            "cold_service_c": self.cold_service_c,
            "ambient_sink_c": self.ambient_sink_c,
            "tier": self.tier,
            "metadata": self.metadata,
        }
        payload.update(dict(self.metadata))
        return payload

    def _context_bracket(self) -> str:
        if self.source_c is not None and self.return_c is not None and self.sink_c is not None:
            return (
                f"[Ts = {_format_c(self.source_c)}, Tr = {_format_c(self.return_c)}, "
                f"T0 = {_format_c(self.sink_c)}]"
            )
        if self.source_c is not None and self.sink_c is not None:
            return f"[Th = {_format_c(self.source_c)}, T0 = {_format_c(self.sink_c)}]"
        if self.cold_service_c is not None and self.ambient_sink_c is not None:
            return (
                f"[Tcold = {_format_c(self.cold_service_c)}, T0 = {_format_c(self.ambient_sink_c)}]"
            )
        if self.method == "solar" and self.sink_c is not None:
            return f"[T0 = {_format_c(self.sink_c)}]"
        if self.energy_basis:
            return f"[basis = {self.energy_basis}]"
        if self.sink_c is not None:
            return f"[T0 = {_format_c(self.sink_c)}]"
        return ""


def _format_c(value: float) -> str:
    text = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return f"{text} C"
