from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class FidelityTierDefinition:
    """Definition of a Quantity + Quality Fidelity Tier."""

    tier: str
    name: str
    summary: str
    minimum_context: tuple[str, ...]

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["minimum_context"] = list(self.minimum_context)
        return payload


FIDELITY_TIERS: tuple[FidelityTierDefinition, ...] = (
    FidelityTierDefinition(
        tier="F0",
        name="scalar legacy",
        summary="Energy quantity only; no Exergy Factor claim.",
        minimum_context=("quantity or power", "unit"),
    ),
    FidelityTierDefinition(
        tier="F1",
        name="presumptive lookup",
        summary="Static lookup or supplied fx suitable for screening.",
        minimum_context=("quantity or power", "unit", "fx"),
    ),
    FidelityTierDefinition(
        tier="F2",
        name="asset-specific",
        summary="Asset-specific or stream-specific factor with declared reference, boundary, and basis.",
        minimum_context=("quantity or power", "unit", "fx", "reference", "boundary", "basis"),
    ),
    FidelityTierDefinition(
        tier="F3",
        name="dynamic interval",
        summary="Interval factor computed from synchronized operating telemetry.",
        minimum_context=(
            "quantity or power",
            "unit",
            "fx",
            "reference",
            "boundary",
            "basis",
            "interval",
        ),
    ),
    FidelityTierDefinition(
        tier="F4",
        name="full vector audit",
        summary="Full state-vector exergy balance with engineering-grade assumptions and closure.",
        minimum_context=("state variables", "reference environment", "boundary", "balance closure"),
    ),
)


_TIER_BY_NAME = {definition.tier: definition for definition in FIDELITY_TIERS}


def normalize_tier(tier: str) -> str:
    """Normalize and validate a Fidelity Tier label."""

    normalized = str(tier).strip().upper()
    if normalized not in _TIER_BY_NAME:
        raise ValueError("tier must be one of F0, F1, F2, F3, or F4")
    return normalized


def get_tier_definition(tier: str) -> FidelityTierDefinition:
    """Return the definition for a Fidelity Tier."""

    return _TIER_BY_NAME[normalize_tier(tier)]


def list_fidelity_tiers() -> tuple[FidelityTierDefinition, ...]:
    """Return the five Fidelity Tier definitions."""

    return FIDELITY_TIERS


def infer_fidelity_tier(record: Mapping[str, object]) -> str:
    """Infer the strongest likely Fidelity Tier from a record's available fields.

    Explicit `tier` or `fidelity_tier` values win. This inference is a practical
    convenience for cleaned records; audited reports should declare the tier.
    """

    explicit = record.get("tier", record.get("fidelity_tier"))
    if explicit not in (None, ""):
        return normalize_tier(str(explicit))

    method = str(record.get("method", "")).lower()
    metadata = record.get("metadata")
    has_fx = record.get("fx") not in (None, "") or record.get("exergy_factor") not in (None, "")
    has_quantity = record.get("quantity") not in (None, "") or record.get("power") not in (None, "")

    if method in {"f4", "state_vector", "full_vector_audit"} or record.get("state_variables"):
        return "F4"
    if (
        method in {"f3", "thermal_interval", "dynamic_interval"}
        or record.get("interval") not in (None, "")
        or record.get("interval_start") not in (None, "")
        or record.get("timestamp") not in (None, "")
        or (isinstance(metadata, Mapping) and metadata.get("interval"))
    ):
        return "F3"
    if (
        record.get("source_c") not in (None, "")
        and record.get("sink_c") not in (None, "")
        or record.get("cold_service_c") not in (None, "")
        and record.get("ambient_sink_c") not in (None, "")
        or method in {"chemical", "solar"}
    ):
        return "F2"
    if has_quantity and has_fx:
        return "F1"
    return "F0"


def conformance_issues(
    record: Mapping[str, object], *, tier: Optional[str] = None
) -> tuple[str, ...]:
    """Return human-readable conformance gaps for the declared or inferred tier."""

    selected = normalize_tier(tier) if tier else infer_fidelity_tier(record)
    issues: list[str] = []

    if (
        record.get("quantity") in (None, "")
        and record.get("power") in (None, "")
        and record.get("notation") in (None, "")
    ):
        issues.append("quantity, power, or notation is required")
    if record.get("unit") in (None, "") and record.get("notation") in (None, ""):
        issues.append("unit is required")

    has_fx = record.get("fx") not in (None, "") or record.get("exergy_factor") not in (None, "")
    if selected != "F0" and not has_fx and record.get("reference_id") in (None, ""):
        issues.append("fx or reference_id is required for F1+ records")

    if selected in {"F2", "F3", "F4"}:
        for field in ("reference", "boundary"):
            if record.get(field) in (None, ""):
                issues.append(f"{field} is required for {selected} records")
        if record.get("basis") in (None, "") and record.get("operating_basis") in (None, ""):
            issues.append(f"basis or operating_basis is required for {selected} records")

    unit = str(record.get("unit", "")).lower()
    method = str(record.get("method", "")).lower()
    if selected in {"F2", "F3", "F4"} and "_th" in unit and method not in {"fluid", "dissipation"}:
        if record.get("source_c") in (None, ""):
            issues.append("source_c is required for F2+ thermal records")
        if record.get("sink_c") in (None, ""):
            issues.append("sink_c is required for F2+ thermal records")

    if selected == "F3":
        metadata = record.get("metadata")
        if (
            record.get("interval") in (None, "")
            and record.get("interval_start") in (None, "")
            and record.get("timestamp") in (None, "")
            and not (
                isinstance(metadata, Mapping)
                and (
                    metadata.get("interval") not in (None, "")
                    or metadata.get("interval_start") not in (None, "")
                    or metadata.get("timestamp") not in (None, "")
                )
            )
        ):
            issues.append(
                f"interval, interval_start, or timestamp is required for {selected} records"
            )

    if selected == "F4":
        metadata = record.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        has_state_vector = bool(
            record.get("state_variables")
            or metadata.get("state_variables")
            or (metadata.get("inlet") and metadata.get("outlet"))
        )
        if not has_state_vector:
            issues.append(
                "state_variables or inlet/outlet state vectors are required for F4 records"
            )
        if not (
            record.get("balance_closure")
            or metadata.get("balance_closure")
            or metadata.get("exergy_balance_closure")
        ):
            issues.append("balance_closure is required for F4 records")

    return tuple(dict.fromkeys(issues))


def tiers_as_dict() -> list[dict]:
    """Return Fidelity Tier definitions as JSON-serializable dictionaries."""

    return [definition.as_dict() for definition in FIDELITY_TIERS]
