from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Mapping, Optional

from .distinguishability import assess_distinguishability
from .model import QuantityQualityRecord
from .units import convert_energy, is_energy_unit, is_power_unit

ENERGY_ACCOUNTING_SCHEMA_VERSION = "1.0"
ENERGY_ACCOUNTING_SCHEMA_ID = (
    "https://raw.githubusercontent.com/cdimurro/quantity-and-quality/"
    "main/data/energy_accounting_request.schema.json"
)

ENERGY_ACCOUNTING_METHODS = (
    "reported",
    "direct",
    "physical_energy_content",
    "total_energy_supply",
    "substitution",
)

_ACCOUNTING_METHOD_ALIASES = {
    "": "reported",
    "reported": "reported",
    "direct": "direct",
    "direct_primary_energy": "direct",
    "physical_energy_content": "physical_energy_content",
    "physical_content": "physical_energy_content",
    "total_energy_supply": "total_energy_supply",
    "tes": "total_energy_supply",
    "substitution": "substitution",
    "substituted": "substitution",
    "fossil_equivalent": "substitution",
    "fossil_fuel_equivalent": "substitution",
}

_REQUEST_FIELDS = {
    "primary",
    "secondary",
    "final",
    "useful",
    "applied_exergy",
    "end_use_exergy_efficiency",
    "service",
    "output_exergy_unit",
    "label",
    "boundary",
}

_STAGE_FIELDS = {
    "quantity",
    "unit",
    "fx",
    "exergy_factor",
    "label",
    "reference",
    "boundary",
    "basis",
    "method",
    "method_id",
    "tier",
    "source_c",
    "return_c",
    "sink_c",
    "cold_service_c",
    "ambient_sink_c",
    "fuel",
    "energy_basis",
    "reference_id",
    "stream_type",
    "quantity_method_id",
    "calculation_inputs",
    "metadata",
    "assumptions",
    "warnings",
    "accounting_method",
    "source_dataset",
    "source_variable",
}

# These are deterministic output fields from QuantityQualityRecord.as_dict().
# Ignoring them lets an agent pass a calculated record directly into a stage
# without weakening typo detection for actual stage inputs.
_DERIVED_STAGE_FIELDS = {
    "type",
    "schema_version",
    "fidelity_tier",
    "notation",
    "full_notation",
    "accessible_exergy",
    "accessible_exergy_unit",
    "accessible_exergy_mwh",
    "capabilities",
    "missing_context",
    "readiness",
    "needs_attention",
    "carrier_registry_version",
    "distinguishability",
    "data_quality_flag",
    "uncertainty",
}

_SERVICE_FIELDS = {"name", "quantity", "unit", "category", "boundary", "notes"}
_APPLIED_FIELDS = {"quantity", "unit", "basis", "boundary"}


class EnergyAccountingError(ValueError):
    """Stable machine-readable error for an invalid end-use account."""

    def __init__(self, code: str, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict:
        payload = {"code": self.code, "message": str(self)}
        if self.field:
            payload["field"] = self.field
        return payload


@dataclass(frozen=True)
class EnergyStage:
    """One state in a primary-secondary-final-useful chain.

    Energy-only statistical data are accepted without an Exergy Factor. A
    substitution-method primary-energy equivalent is retained as reported but
    never converted to exergy because it is counterfactual, not a physical
    stream at that magnitude.
    """

    stage: str
    quantity: float
    unit: str
    record: Optional[QuantityQualityRecord] = None
    accounting_method: str = "reported"
    label: str = ""
    boundary: str = ""
    basis: str = ""
    source_dataset: str = ""
    source_variable: str = ""

    @property
    def energy_mwh(self) -> float:
        return convert_energy(self.quantity, self.unit, "MWh")

    @property
    def energy_quantity_type(self) -> str:
        if self.accounting_method == "substitution":
            return "counterfactual_energy_equivalent"
        return "physical_or_reported_energy"

    @property
    def exergy_mwh(self) -> Optional[float]:
        if self.record is None or self.accounting_method == "substitution":
            return None
        return self.energy_mwh * self.record.exergy_factor

    @property
    def anergy_mwh(self) -> Optional[float]:
        # E = X + A is directly reportable only on a complete energy basis for
        # which fx <= 1. LHV and other partial denominators may legitimately
        # produce fx > 1, so a negative "anergy" must never be invented.
        if self.record is None or self.record.exergy_factor > 1.0:
            return None
        exergy = self.exergy_mwh
        return self.energy_mwh - exergy if exergy is not None else None

    def as_dict(self) -> dict:
        payload = {
            "stage": self.stage,
            "quantity": self.quantity,
            "unit": self.unit,
            "energy_mwh": self.energy_mwh,
            "accounting_method": self.accounting_method,
            "energy_quantity_type": self.energy_quantity_type,
            "thermodynamic_conversion_allowed": self.accounting_method != "substitution",
            "quality_status": (
                "not_applicable_to_counterfactual_equivalent"
                if self.accounting_method == "substitution"
                else "reported"
                if self.record is not None
                else "not_supplied"
            ),
        }
        if self.record is not None:
            payload.update(
                {
                    "exergy_factor": self.record.exergy_factor,
                    "fx": self.record.exergy_factor,
                    "exergy_mwh": self.exergy_mwh,
                    "exergy_unit": "MWh_ex",
                    "distinguishability": assess_distinguishability(self.record).as_dict(),
                    "method_id": self.record.method_identifier,
                }
            )
            if self.anergy_mwh is not None:
                payload["anergy_mwh"] = self.anergy_mwh
            if self.record.reference:
                payload["reference"] = self.record.reference
        else:
            payload["missing_quality"] = [
                "physical_energy_basis" if self.accounting_method == "substitution" else "fx"
            ]
        for key, value in {
            "label": self.label,
            "boundary": self.boundary,
            "basis": self.basis,
            "source_dataset": self.source_dataset,
            "source_variable": self.source_variable,
        }.items():
            if value:
                payload[key] = value
        return payload


@dataclass(frozen=True)
class EnergyService:
    """A desired outcome measured outside the energy-unit system."""

    name: str
    quantity: float
    unit: str
    category: str = ""
    boundary: str = ""
    notes: str = ""

    def as_dict(self, *, applied_exergy_mwh: Optional[float] = None) -> dict:
        payload = {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "type": "energy_service",
            "energy_unit": False,
        }
        if self.category:
            payload["category"] = self.category
        if self.boundary:
            payload["boundary"] = self.boundary
        if self.notes:
            payload["notes"] = self.notes
        if applied_exergy_mwh is not None and self.quantity > 0:
            payload["applied_exergy_intensity"] = applied_exergy_mwh / self.quantity
            payload["applied_exergy_intensity_unit"] = f"MWh_ex/{self.unit}"
            if applied_exergy_mwh > 0:
                payload["service_productivity"] = self.quantity / applied_exergy_mwh
                payload["service_productivity_unit"] = f"{self.unit}/MWh_ex"
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class EndUseAccounting:
    """A compact primary-secondary-final-useful-Applied Exergy account."""

    primary: Optional[EnergyStage] = None
    secondary: Optional[EnergyStage] = None
    final: Optional[EnergyStage] = None
    useful: Optional[EnergyStage] = None
    applied_exergy_mwh: Optional[float] = None
    applied_exergy_basis: str = ""
    applied_exergy_boundary: str = ""
    service: Optional[EnergyService] = None
    output_exergy_unit: str = "MWh_ex"
    label: str = ""
    boundary: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def stages(self) -> dict[str, EnergyStage]:
        values = {
            "primary": self.primary,
            "secondary": self.secondary,
            "final": self.final,
            "useful": self.useful,
        }
        return {name: stage for name, stage in values.items() if stage is not None}

    @property
    def missing(self) -> tuple[str, ...]:
        missing = [name for name in ("primary", "final", "useful") if name not in self.stages]
        if self.applied_exergy_mwh is None:
            missing.append("applied_exergy")
        for name, stage in self.stages.items():
            if stage.exergy_mwh is None:
                missing.append(
                    f"{name}.physical_energy_basis"
                    if stage.accounting_method == "substitution"
                    else f"{name}.fx"
                )
        return tuple(missing)

    @property
    def complete(self) -> bool:
        return not self.missing

    def as_dict(self) -> dict:
        applied = None
        if self.applied_exergy_mwh is not None:
            applied = convert_energy(
                self.applied_exergy_mwh,
                "MWh_ex",
                self.output_exergy_unit,
            )
        payload = {
            "schema_version": ENERGY_ACCOUNTING_SCHEMA_VERSION,
            "type": "end_use_energy_account",
            "label": self.label,
            "boundary": self.boundary,
            "complete": self.complete,
            "missing": list(self.missing),
            "stages": {name: stage.as_dict() for name, stage in self.stages.items()},
            "applied_exergy": applied,
            "applied_exergy_unit": self.output_exergy_unit if applied is not None else None,
            "applied_exergy_mwh": self.applied_exergy_mwh,
            "applied_exergy_basis": self.applied_exergy_basis,
            "applied_exergy_boundary": self.applied_exergy_boundary,
            "efficiencies": _efficiencies(self),
            "warnings": list(self.warnings),
            "terminology_version": ENERGY_ACCOUNTING_SCHEMA_VERSION,
        }
        if self.service:
            payload["service"] = self.service.as_dict(applied_exergy_mwh=self.applied_exergy_mwh)
        return {key: value for key, value in payload.items() if value not in (None, "")}


def account_energy_chain(request: Mapping[str, object]) -> EndUseAccounting:
    """Build a partial or complete end-use energy and exergy account.

    Applied Exergy is the exergy that crosses the last device-to-task boundary.
    It can be supplied directly, calculated from the useful-energy output, or
    calculated from final exergy and a declared end-use exergy efficiency.
    """

    if not isinstance(request, Mapping):
        raise EnergyAccountingError("invalid_request", "request must be an object")
    data = dict(request)
    unknown = sorted(set(data) - _REQUEST_FIELDS)
    if unknown:
        raise EnergyAccountingError(
            "unknown_field",
            f"unknown input field: {unknown[0]}",
            field=unknown[0],
        )

    primary = _optional_stage("primary", data.get("primary"))
    secondary = _optional_stage("secondary", data.get("secondary"))
    final = _optional_stage("final", data.get("final"))
    useful = _optional_stage("useful", data.get("useful"))
    if not any((primary, secondary, final, useful, data.get("applied_exergy"))):
        raise EnergyAccountingError(
            "missing_input",
            "provide at least one energy stage or applied_exergy",
        )

    output_unit = str(data.get("output_exergy_unit", "MWh_ex")).strip()
    _require_exergy_unit(output_unit, "output_exergy_unit")

    candidates: list[tuple[float, str, str]] = []
    if useful is not None and useful.exergy_mwh is not None:
        candidates.append(
            (
                useful.exergy_mwh,
                "useful_energy_times_useful_fx",
                useful.boundary or "end-use device output to task",
            )
        )

    eta = _optional_number(data, "end_use_exergy_efficiency")
    if eta is not None:
        if not 0 <= eta <= 1:
            raise EnergyAccountingError(
                "invalid_value",
                "end_use_exergy_efficiency must be between 0 and 1",
                field="end_use_exergy_efficiency",
            )
        if final is None:
            raise EnergyAccountingError(
                "missing_input",
                "final stage is required with end_use_exergy_efficiency",
                field="final",
            )
        if final.exergy_mwh is None:
            raise EnergyAccountingError(
                "missing_quality",
                "final.fx is required with end_use_exergy_efficiency",
                field="final.fx",
            )
        candidates.append(
            (
                final.exergy_mwh * eta,
                "final_exergy_times_end_use_exergy_efficiency",
                str(data.get("boundary", "end-use device output to task")),
            )
        )

    direct = _optional_applied_exergy(data.get("applied_exergy"))
    if direct is not None:
        candidates.append(direct)

    applied_mwh: Optional[float] = None
    applied_basis = ""
    applied_boundary = ""
    if candidates:
        applied_mwh, applied_basis, applied_boundary = candidates[0]
        for candidate, basis, _ in candidates[1:]:
            if not math.isclose(candidate, applied_mwh, rel_tol=1e-6, abs_tol=1e-9):
                raise EnergyAccountingError(
                    "accounting_inconsistency",
                    "the supplied Applied Exergy paths do not agree",
                    field="applied_exergy",
                )
            applied_basis = f"{applied_basis}; confirmed by {basis}"

    if final is not None and final.exergy_mwh is not None and applied_mwh is not None:
        tolerance = max(1e-9, final.exergy_mwh * 1e-9)
        if applied_mwh > final.exergy_mwh + tolerance:
            raise EnergyAccountingError(
                "accounting_inconsistency",
                "Applied Exergy cannot exceed final exergy in a single-input end-use chain",
                field="applied_exergy",
            )

    warnings = []
    if (
        primary is not None
        and final is not None
        and primary.exergy_mwh is not None
        and final.exergy_mwh is not None
        and final.exergy_mwh > primary.exergy_mwh
    ):
        warnings.append(
            "final exergy exceeds primary exergy; check boundaries, aggregation, and primary-energy convention"
        )
    for stage in (primary, secondary, final, useful):
        if stage is None:
            continue
        if stage.accounting_method == "substitution":
            warnings.append(
                f"{stage.stage} energy uses the substitution method; its counterfactual "
                "energy equivalent is retained but is not converted to exergy"
            )
        elif stage.record is None:
            warnings.append(
                f"{stage.stage} exergy is not reported because no Exergy Factor was supplied"
            )
        elif stage.anergy_mwh is None:
            warnings.append(
                f"{stage.stage} anergy is not reported because fx > 1 uses a partial energy denominator"
            )
    if final is not None and final.exergy_mwh is None and applied_mwh is not None:
        warnings.append(
            "Applied Exergy could not be checked against final exergy because final.fx is unavailable"
        )

    service = _optional_service(data.get("service"))
    return EndUseAccounting(
        primary=primary,
        secondary=secondary,
        final=final,
        useful=useful,
        applied_exergy_mwh=applied_mwh,
        applied_exergy_basis=applied_basis,
        applied_exergy_boundary=applied_boundary,
        service=service,
        output_exergy_unit=output_unit,
        label=str(data.get("label", "")).strip(),
        boundary=str(data.get("boundary", "")).strip(),
        warnings=tuple(warnings),
    )


def accounting_capabilities() -> dict:
    """Return definitions and accepted request paths for agents and users."""

    return {
        "schema_version": ENERGY_ACCOUNTING_SCHEMA_VERSION,
        "purpose": (
            "Keep energy and exergy accounting distinct from the non-energy service outcome."
        ),
        "request_schema": ENERGY_ACCOUNTING_SCHEMA_ID,
        "stages": [
            "primary",
            "secondary",
            "final",
            "useful",
            "applied_exergy",
            "service",
        ],
        "energy_accounting_methods": list(ENERGY_ACCOUNTING_METHODS),
        "dataset_compatibility": {
            "energy_only_stages": True,
            "provenance_fields": ["source_dataset", "source_variable"],
            "substitution_exergy_conversion": False,
            "supported_energy_units_include": ["TWh", "GWh", "MWh", "TJ", "PJ", "EJ"],
        },
        "applied_exergy_paths": [
            "useful.quantity * useful.fx",
            "final exergy * end_use_exergy_efficiency",
            "direct measured or independently calculated applied_exergy",
        ],
        "definitions": accounting_definitions(),
        "rules": [
            "Applied Exergy is exergy crossing the final device-to-task boundary.",
            "Useful energy is the end-use device output and may contain both exergy and anergy.",
            "Applied Exergy corresponds to useful exergy/useful work in societal exergy literature.",
            "Energy services use outcome units, never J, Wh, or another energy unit.",
            "Secondary energy is an optional transformed, transportable carrier boundary before final delivery.",
            "Energy-only records are accepted when fx is unavailable; exergy is then left unreported.",
            "Substitution-method primary energy is a counterfactual equivalent and is never multiplied by fx.",
            "Energy quantities need not decrease across stages; heat pumps can deliver useful heat above final electricity input.",
            "Applied Exergy cannot exceed final exergy for the single-input chain represented here.",
        ],
        "example": {
            "label": "Electric motor providing shaft work",
            "primary": {
                "quantity": 2.5,
                "unit": "MWh_fuel",
                "fx": 1.04,
                "accounting_method": "physical_energy_content",
            },
            "secondary": {"quantity": 1.05, "unit": "MWh_e", "fx": 1.0},
            "final": {"quantity": 1, "unit": "MWh_e", "fx": 1.0},
            "useful": {"quantity": 0.9, "unit": "MWh_mech", "fx": 1.0},
            "service": {
                "name": "Conveyor movement",
                "quantity": 12000,
                "unit": "tonne_metre",
                "category": "material movement",
            },
        },
    }


def accounting_definitions() -> dict:
    return {
        "primary_energy": (
            "Energy at the resource or first statistical supply boundary, using a declared primary-energy convention."
        ),
        "secondary_energy": (
            "Energy after primary conversion into a transportable carrier, such as electricity, "
            "refined fuel, or district heat, and before delivery to the final consumer."
        ),
        "final_energy": "Energy carrier delivered to the end user before the end-use device.",
        "useful_energy": (
            "Energy output of the end-use device in the form delivered to the task; it may contain exergy and anergy."
        ),
        "primary_exergy": (
            "Physical primary energy multiplied by its boundary-specific Exergy Factor. "
            "A substitution-method energy equivalent is not a physical basis for this calculation."
        ),
        "secondary_exergy": "Secondary energy multiplied by its boundary-specific Exergy Factor.",
        "final_exergy": "Final energy multiplied by its boundary-specific Exergy Factor.",
        "applied_exergy": (
            "Exergy that reaches and crosses the last device-to-task boundary. This project term corresponds to useful exergy or useful work in societal exergy accounting."
        ),
        "energy_service": (
            "The desired societal outcome produced with Applied Exergy and other inputs, measured in an outcome unit rather than an energy unit."
        ),
        "substitution_method": (
            "A statistical primary-energy convention that divides non-fossil electricity by an assumed "
            "thermal efficiency to report a counterfactual fossil-input equivalent."
        ),
        "physical_energy_content_method": (
            "A primary-energy convention based on physical energy content or total energy supply, "
            "without a fossil-equivalent adjustment for wind, solar PV, or hydropower."
        ),
    }


def _optional_stage(stage: str, value: object) -> Optional[EnergyStage]:
    if value is None:
        return None
    if isinstance(value, QuantityQualityRecord):
        record = value
        accounting_stage = EnergyStage(
            stage=stage,
            quantity=record.quantity,
            unit=record.unit,
            record=record,
            label=record.label or "",
            boundary=record.boundary,
            basis=record.basis,
        )
    elif isinstance(value, Mapping):
        accounting_stage = _stage_from_mapping(stage, value)
    else:
        raise EnergyAccountingError(
            "invalid_type", f"{stage} must be an energy record object", field=stage
        )
    if not is_energy_unit(accounting_stage.unit):
        raise EnergyAccountingError(
            "unsupported_unit",
            f"{stage}.unit must be an energy unit, not a power or service unit",
            field=f"{stage}.unit",
        )
    return accounting_stage


def _stage_from_mapping(stage: str, value: Mapping[str, object]) -> EnergyStage:
    data = dict(value)
    unknown = sorted(set(data) - _STAGE_FIELDS - _DERIVED_STAGE_FIELDS)
    if unknown:
        raise EnergyAccountingError(
            "unknown_field",
            f"unknown {stage} field: {unknown[0]}",
            field=f"{stage}.{unknown[0]}",
        )
    quantity = _required_number(data, "quantity", prefix=stage)
    if quantity < 0:
        raise EnergyAccountingError(
            "invalid_value", f"{stage}.quantity must be nonnegative", field=f"{stage}.quantity"
        )
    unit = str(data.get("unit", "")).strip()
    if not unit:
        raise EnergyAccountingError(
            "missing_input", f"{stage}.unit is required", field=f"{stage}.unit"
        )
    factor = _optional_factor(data, stage)
    accounting_method = _normalize_accounting_method(
        data.get("accounting_method"), f"{stage}.accounting_method"
    )
    if accounting_method == "substitution" and stage != "primary":
        raise EnergyAccountingError(
            "invalid_accounting_basis",
            "the substitution method is a primary-energy accounting convention",
            field=f"{stage}.accounting_method",
        )
    if accounting_method == "substitution" and factor is not None:
        raise EnergyAccountingError(
            "invalid_accounting_basis",
            "substitution-method energy is a counterfactual equivalent and cannot carry a physical fx",
            field=f"{stage}.fx",
        )
    boundary = str(data.get("boundary", f"{stage} energy boundary"))
    basis = str(data.get("basis", ""))
    label = str(data.get("label", "")).strip()
    record = None
    if factor is not None:
        record = QuantityQualityRecord(
            quantity=quantity,
            unit=unit,
            exergy_factor=factor,
            reference=str(data.get("reference", "")),
            boundary=boundary,
            basis=basis,
            method=str(data.get("method", "supplied")),
            tier=str(data.get("tier", "")),
            label=label or None,
            source_c=_optional_float(data.get("source_c"), f"{stage}.source_c"),
            return_c=_optional_float(data.get("return_c"), f"{stage}.return_c"),
            sink_c=_optional_float(data.get("sink_c"), f"{stage}.sink_c"),
            cold_service_c=_optional_float(data.get("cold_service_c"), f"{stage}.cold_service_c"),
            ambient_sink_c=_optional_float(data.get("ambient_sink_c"), f"{stage}.ambient_sink_c"),
            fuel=_optional_text(data.get("fuel")),
            energy_basis=_optional_text(data.get("energy_basis")),
            reference_id=_optional_text(data.get("reference_id")),
            method_id=_optional_text(data.get("method_id")),
            stream_type=_optional_text(data.get("stream_type")),
            quantity_method_id=_optional_text(data.get("quantity_method_id")),
            calculation_inputs=_mapping(data.get("calculation_inputs")),
            assumptions=_string_tuple(data.get("assumptions")),
            warnings=_string_tuple(data.get("warnings")),
            metadata=_mapping(data.get("metadata")),
        )
    return EnergyStage(
        stage=stage,
        quantity=quantity,
        unit=unit,
        record=record,
        accounting_method=accounting_method,
        label=label,
        boundary=boundary,
        basis=basis,
        source_dataset=str(data.get("source_dataset", "")).strip(),
        source_variable=str(data.get("source_variable", "")).strip(),
    )


def _optional_applied_exergy(value: object) -> Optional[tuple[float, str, str]]:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise EnergyAccountingError(
            "invalid_type", "applied_exergy must be an object", field="applied_exergy"
        )
    data = dict(value)
    unknown = sorted(set(data) - _APPLIED_FIELDS)
    if unknown:
        raise EnergyAccountingError(
            "unknown_field",
            f"unknown applied_exergy field: {unknown[0]}",
            field=f"applied_exergy.{unknown[0]}",
        )
    quantity = _required_number(data, "quantity", prefix="applied_exergy")
    if quantity < 0:
        raise EnergyAccountingError(
            "invalid_value",
            "applied_exergy.quantity must be nonnegative",
            field="applied_exergy.quantity",
        )
    unit = str(data.get("unit", "")).strip()
    _require_exergy_unit(unit, "applied_exergy.unit")
    return (
        convert_energy(quantity, unit, "MWh_ex"),
        str(data.get("basis", "directly declared Applied Exergy")),
        str(data.get("boundary", "end-use device output to task")),
    )


def _optional_service(value: object) -> Optional[EnergyService]:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise EnergyAccountingError("invalid_type", "service must be an object", field="service")
    data = dict(value)
    unknown = sorted(set(data) - _SERVICE_FIELDS)
    if unknown:
        raise EnergyAccountingError(
            "unknown_field",
            f"unknown service field: {unknown[0]}",
            field=f"service.{unknown[0]}",
        )
    name = str(data.get("name", "")).strip()
    unit = str(data.get("unit", "")).strip()
    if not name:
        raise EnergyAccountingError(
            "missing_input", "service.name is required", field="service.name"
        )
    if not unit:
        raise EnergyAccountingError(
            "missing_input", "service.unit is required", field="service.unit"
        )
    if _is_standard_energy_or_power_unit(unit):
        raise EnergyAccountingError(
            "invalid_service_unit",
            "service.unit must describe an outcome, not energy or power",
            field="service.unit",
        )
    quantity = _required_number(data, "quantity", prefix="service")
    if quantity < 0:
        raise EnergyAccountingError(
            "invalid_value", "service.quantity must be nonnegative", field="service.quantity"
        )
    return EnergyService(
        name=name,
        quantity=quantity,
        unit=unit,
        category=str(data.get("category", "")).strip(),
        boundary=str(data.get("boundary", "")).strip(),
        notes=str(data.get("notes", "")).strip(),
    )


def _efficiencies(account: EndUseAccounting) -> dict:
    values = {}
    if account.primary and account.secondary:
        values["primary_to_secondary_energy"] = _ratio(
            account.secondary.energy_mwh, account.primary.energy_mwh
        )
        _add_exergy_ratio(
            values,
            "primary_to_secondary_exergy",
            account.secondary.exergy_mwh,
            account.primary.exergy_mwh,
        )
    if account.secondary and account.final:
        values["secondary_to_final_energy"] = _ratio(
            account.final.energy_mwh, account.secondary.energy_mwh
        )
        _add_exergy_ratio(
            values,
            "secondary_to_final_exergy",
            account.final.exergy_mwh,
            account.secondary.exergy_mwh,
        )
    if account.primary and account.final:
        values["primary_to_final_energy"] = _ratio(
            account.final.energy_mwh, account.primary.energy_mwh
        )
        _add_exergy_ratio(
            values,
            "primary_to_final_exergy",
            account.final.exergy_mwh,
            account.primary.exergy_mwh,
        )
    if account.final and account.useful:
        values["final_to_useful_energy"] = _ratio(
            account.useful.energy_mwh, account.final.energy_mwh
        )
    if (
        account.final
        and account.final.exergy_mwh is not None
        and account.applied_exergy_mwh is not None
    ):
        values["final_to_applied_exergy"] = _ratio(
            account.applied_exergy_mwh, account.final.exergy_mwh
        )
    if (
        account.primary
        and account.primary.exergy_mwh is not None
        and account.applied_exergy_mwh is not None
    ):
        values["primary_to_applied_exergy"] = _ratio(
            account.applied_exergy_mwh, account.primary.exergy_mwh
        )
    return values


def _add_exergy_ratio(
    values: dict,
    name: str,
    numerator: Optional[float],
    denominator: Optional[float],
) -> None:
    if numerator is not None and denominator is not None:
        values[name] = _ratio(numerator, denominator)


def _ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def _factor(data: Mapping[str, object], stage: str) -> float:
    fx = data.get("fx")
    exergy_factor = data.get("exergy_factor")
    if fx is None and exergy_factor is None:
        raise EnergyAccountingError(
            "missing_input",
            f"{stage}.fx or {stage}.exergy_factor is required",
            field=f"{stage}.fx",
        )
    if fx is not None and exergy_factor is not None:
        left = _finite_number(fx, f"{stage}.fx")
        right = _finite_number(exergy_factor, f"{stage}.exergy_factor")
        if not math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12):
            raise EnergyAccountingError(
                "accounting_inconsistency",
                f"{stage}.fx and {stage}.exergy_factor do not agree",
                field=f"{stage}.fx",
            )
        factor = left
    else:
        factor = _finite_number(fx if fx is not None else exergy_factor, f"{stage}.fx")
    if factor < 0:
        raise EnergyAccountingError(
            "invalid_value", f"{stage}.fx must be nonnegative", field=f"{stage}.fx"
        )
    return factor


def _optional_factor(data: Mapping[str, object], stage: str) -> Optional[float]:
    if data.get("fx") is None and data.get("exergy_factor") is None:
        return None
    return _factor(data, stage)


def _normalize_accounting_method(value: object, field: str) -> str:
    key = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    key = "_".join(key.split())
    method = _ACCOUNTING_METHOD_ALIASES.get(key)
    if method is None:
        accepted = ", ".join(ENERGY_ACCOUNTING_METHODS)
        raise EnergyAccountingError(
            "invalid_value",
            f"{field} must be one of: {accepted}",
            field=field,
        )
    return method


def _required_number(data: Mapping[str, object], field: str, *, prefix: str) -> float:
    if field not in data:
        name = f"{prefix}.{field}"
        raise EnergyAccountingError("missing_input", f"{name} is required", field=name)
    return _finite_number(data[field], f"{prefix}.{field}")


def _optional_number(data: Mapping[str, object], field: str) -> Optional[float]:
    if field not in data or data[field] is None:
        return None
    return _finite_number(data[field], field)


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise EnergyAccountingError("invalid_type", f"{field} must be numeric", field=field)
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise EnergyAccountingError(
            "invalid_type", f"{field} must be numeric", field=field
        ) from exc
    if not math.isfinite(number):
        raise EnergyAccountingError("invalid_value", f"{field} must be finite", field=field)
    return number


def _optional_float(value: object, field: str) -> Optional[float]:
    if value is None:
        return None
    return _finite_number(value, field)


def _require_exergy_unit(unit: str, field: str) -> None:
    if not unit:
        raise EnergyAccountingError("missing_input", f"{field} is required", field=field)
    if re.search(r"_ex(?:_|$)", unit, re.IGNORECASE) is None or not is_energy_unit(unit):
        raise EnergyAccountingError(
            "unsupported_unit",
            f"{field} must be an energy unit with an _ex suffix, such as MWh_ex",
            field=field,
        )


def _is_standard_energy_or_power_unit(unit: str) -> bool:
    try:
        return is_energy_unit(unit) or is_power_unit(unit)
    except ValueError:
        return False


def _optional_text(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _mapping(value: object) -> Mapping[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)
