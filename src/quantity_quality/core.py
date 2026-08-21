from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Optional, Tuple, Union

Number = Union[int, float]
T_SUN_K = 5778.0
STANDARD_AMBIENT_K = 293.15


@dataclass(frozen=True)
class ReferenceContext:
    """Metadata that makes an Exergy Factor interpretable."""

    reference: str
    boundary: str
    operating_basis: str
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class ReferenceEnvironment:
    """Standard reference environment metadata for comparable reporting."""

    id: str = "standard_ambient_20c_101325pa"
    temperature_k: float = STANDARD_AMBIENT_K
    pressure_pa: float = 101325.0
    source: str = "standard ambient reporting convention"
    is_site_specific: bool = False

    def __post_init__(self) -> None:
        _require_positive(self.temperature_k, "temperature_k")
        _require_positive(self.pressure_pa, "pressure_pa")

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EnergyReport:
    """A quantity-plus-quality record for accumulated energy."""

    quantity: float
    unit: str
    exergy_factor: float
    context: ReferenceContext
    label: Optional[str] = None

    def __post_init__(self) -> None:
        _require_nonnegative(self.quantity, "quantity")
        _require_valid_factor(self.exergy_factor)
        if not self.unit:
            raise ValueError("unit is required")

    @property
    def accessible_exergy(self) -> float:
        return accessible_exergy(self.quantity, self.exergy_factor)

    @property
    def accessible_exergy_unit(self) -> str:
        return exergy_unit(self.unit)

    def as_dict(self) -> dict:
        return {
            "type": "energy",
            "label": self.label,
            "quantity": self.quantity,
            "unit": self.unit,
            "exergy_factor": self.exergy_factor,
            "notation": format_energy_notation(self.quantity, self.unit, self.exergy_factor),
            "accessible_exergy": self.accessible_exergy,
            "accessible_exergy_unit": self.accessible_exergy_unit,
            "context": self.context.as_dict(),
        }


@dataclass(frozen=True)
class PowerReport:
    """A quantity-plus-quality record for an energy or work rate."""

    power: float
    unit: str
    exergy_factor: float
    context: ReferenceContext
    label: Optional[str] = None

    def __post_init__(self) -> None:
        _require_nonnegative(self.power, "power")
        _require_valid_factor(self.exergy_factor)
        if not self.unit:
            raise ValueError("unit is required")

    @property
    def accessible_exergy_rate(self) -> float:
        return accessible_exergy(self.power, self.exergy_factor)

    @property
    def accessible_exergy_rate_unit(self) -> str:
        return exergy_unit(self.unit)

    def as_dict(self) -> dict:
        return {
            "type": "power",
            "label": self.label,
            "power": self.power,
            "unit": self.unit,
            "exergy_factor": self.exergy_factor,
            "notation": format_energy_notation(self.power, self.unit, self.exergy_factor),
            "accessible_exergy_rate": self.accessible_exergy_rate,
            "accessible_exergy_rate_unit": self.accessible_exergy_rate_unit,
            "context": self.context.as_dict(),
        }


@dataclass(frozen=True)
class ParsedNotation:
    """Parsed representation of `1 MWh_e, fx = 1.0` and of the full declaration.

    The declaration bracket fields are what make a record checkable by whoever
    receives it, so they survive parsing rather than being discarded as prose.
    """

    quantity: float
    unit: str
    exergy_factor: float
    source_c: Optional[float] = None
    return_c: Optional[float] = None
    sink_c: Optional[float] = None
    cold_service_c: Optional[float] = None
    energy_basis: Optional[str] = None

    @property
    def is_fully_specified(self) -> bool:
        """True when the record carries what a reader needs to re-derive `fx`."""

        return self.sink_c is not None and (
            self.source_c is not None or self.cold_service_c is not None
        )


def accessible_exergy(quantity_or_power: Number, exergy_factor: Number) -> float:
    """Return accessible exergy for an energy quantity or power rate."""

    quantity = float(quantity_or_power)
    factor = float(exergy_factor)
    _require_nonnegative(quantity, "quantity_or_power")
    _require_valid_factor(factor)
    return quantity * factor


def format_exergy_factor(exergy_factor: Number, precision: int = 3) -> str:
    """Format an Exergy Factor for public notation.

    A COMPUTED factor keeps its trailing zeros: `0.170`, not `0.17`, and `0.730`,
    not `0.73`. Those digits are the reader's evidence of the precision being
    claimed, and dropping them made the published figure look different from the
    value a reader recomputes (1 - 293.15/353.15 = 0.16990 -> 0.170).

    An EXACT factor is not padded. Electricity is 1 by definition, not 1 measured
    to three decimals, so it reads `fx = 1.0`. Padding it to `1.000` dresses a
    definition up as a measurement and is just noise on the page.

    The quantity is never padded either — `1 MWh`, not `1.000 MWh`.
    """

    factor = float(exergy_factor)
    _require_valid_factor(factor)
    if factor == int(factor):
        return f"{int(factor)}.0"
    return f"{factor:.{precision}f}"


def format_energy_notation(
    quantity_or_power: Number,
    unit: str,
    exergy_factor: Number,
    *,
    precision: int = 3,
) -> str:
    """Return short adoption notation, for example `1 MWh_th, fx = 0.730`."""

    quantity = float(quantity_or_power)
    _require_nonnegative(quantity, "quantity_or_power")
    if not unit:
        raise ValueError("unit is required")
    return (
        f"{_format_number(quantity, precision=precision)} {unit}, "
        f"fx = {format_exergy_factor(exergy_factor, precision=precision)}"
    )


def exergy_unit(unit: str) -> str:
    """Return a readable exergy unit from an energy or power unit.

    Examples:
    - MWh_th -> MWh_ex
    - MWh_LHV -> MWh_ex
    - MW -> MW_ex
    - GJ -> GJ_ex
    """

    if not unit:
        raise ValueError("unit is required")
    base = unit.split("_", 1)[0]
    return f"{base}_ex"


# A temperature inside the declaration bracket: `80 C`, `80C`, `80°C`, `353.15 K`.
# The degree sign is optional on input because the paper typesets `80°C` while the
# wire format stays ASCII, and a reader pasting either one must be understood.
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_TEMP = rf"(?P<{{name}}>{_NUMBER})\s*(?:°|º)?\s*(?P<{{name}}_unit>[CKF])?"

_NOTATION_RE = re.compile(
    rf"^\s*(?P<quantity>{_NUMBER})\s+"
    r"(?P<unit>[^,\[]+?)\s*,\s*"
    r"(?:f_X|fx|fX)\s*=\s*"
    rf"(?P<factor>{_NUMBER})"
    # The declaration bracket is OPTIONAL, so the short form still parses. When it
    # is present it is what makes the record independently checkable, and this
    # parser refused it for as long as it existed: the pattern ended at the factor,
    # so `full_notation` — the library's own canonical output — raised ValueError.
    r"(?:\s*\[\s*(?P<bracket>[^\]]*)\s*\])?\s*$",
    re.IGNORECASE,
)

_BRACKET_TH_RE = re.compile(r"\bT_?h(?:ot)?\s*=\s*" + _TEMP.format(name="th"), re.IGNORECASE)
_BRACKET_TS_RE = re.compile(r"\bT_?s(?:upply)?\s*=\s*" + _TEMP.format(name="ts"), re.IGNORECASE)
_BRACKET_TR_RE = re.compile(r"\bT_?r(?:eturn)?\s*=\s*" + _TEMP.format(name="tr"), re.IGNORECASE)
_BRACKET_T0_RE = re.compile(r"\bT_?0\s*=\s*" + _TEMP.format(name="t0"), re.IGNORECASE)
_BRACKET_TCOLD_RE = re.compile(r"\bT_?cold\s*=\s*" + _TEMP.format(name="tcold"), re.IGNORECASE)
_BRACKET_BASIS_RE = re.compile(r"\bbasis\s*=\s*(?P<basis>[^,\]]+)", re.IGNORECASE)


def _temp_to_c(value: Optional[str], unit: Optional[str]) -> Optional[float]:
    """Normalise a bracket temperature to Celsius, honouring an explicit K or F."""

    if value is None:
        return None
    number = float(value)
    suffix = (unit or "C").upper()
    if suffix == "K":
        return number - 273.15
    if suffix == "F":
        return (number - 32.0) * 5.0 / 9.0
    return number


def parse_energy_notation(text: str) -> ParsedNotation:
    """Parse `1 MWh_e, fx = 1.0` and `1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]`.

    Both the short form and the full declaration round-trip. `°C` is accepted but
    not required, and a bracket temperature may state `K` or `F` explicitly.
    """

    match = _NOTATION_RE.match(text)
    if not match:
        raise ValueError(
            "expected notation like '1 MWh_e, fx = 1.0' or "
            "'1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]'"
        )
    quantity = float(match.group("quantity"))
    unit = match.group("unit").strip()
    factor = float(match.group("factor"))
    _require_nonnegative(quantity, "quantity")
    _require_valid_factor(factor)
    if not unit:
        raise ValueError("unit is required")

    source_c = return_c = sink_c = cold_c = None
    basis = None
    bracket = match.group("bracket")
    if bracket:
        if (found := _BRACKET_TH_RE.search(bracket)) is not None:
            source_c = _temp_to_c(found.group("th"), found.group("th_unit"))
        elif (found := _BRACKET_TS_RE.search(bracket)) is not None:
            source_c = _temp_to_c(found.group("ts"), found.group("ts_unit"))
        if (found := _BRACKET_TR_RE.search(bracket)) is not None:
            return_c = _temp_to_c(found.group("tr"), found.group("tr_unit"))
        if (found := _BRACKET_T0_RE.search(bracket)) is not None:
            sink_c = _temp_to_c(found.group("t0"), found.group("t0_unit"))
        if (found := _BRACKET_TCOLD_RE.search(bracket)) is not None:
            cold_c = _temp_to_c(found.group("tcold"), found.group("tcold_unit"))
        if (found := _BRACKET_BASIS_RE.search(bracket)) is not None:
            basis = found.group("basis").strip()

    return ParsedNotation(
        quantity=quantity,
        unit=unit,
        exergy_factor=factor,
        source_c=source_c,
        return_c=return_c,
        sink_c=sink_c,
        cold_service_c=cold_c,
        energy_basis=basis,
    )


@dataclass(frozen=True)
class NotationVerification:
    """The result of independently re-deriving a record's Exergy Factor.

    This is the property the notation exists for. A record that declares its
    source and reference temperatures can be checked by whoever receives it,
    without trusting the sender, the tool that produced it, or this library —
    the arithmetic is one division.
    """

    verifiable: bool
    agrees: bool
    stated_exergy_factor: float
    recomputed_exergy_factor: Optional[float]
    equation: str
    substitution: str
    difference: Optional[float]
    tolerance: float
    reason: str = ""

    def __str__(self) -> str:
        if not self.verifiable:
            return f"not independently verifiable: {self.reason}"
        mark = "OK" if self.agrees else "MISMATCH"
        return (
            f"{self.equation} = {self.substitution} = {self.recomputed_exergy_factor:.3f}  [{mark}]"
        )


def verify_notation(text: str, *, tolerance: Optional[float] = None) -> NotationVerification:
    """Re-derive the Exergy Factor stated in a notation string, from its own bracket.

    >>> print(verify_notation("1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]"))
    fx = 1 - T0/Th = 1 - 293.15/353.15 = 0.170  [OK]

    A record without a declaration bracket is reported as not verifiable rather
    than as wrong: nothing has been contradicted, there is simply nothing to check
    against. That distinction matters — silently returning False for a short-form
    record would brand every legitimate `1 MWh, fx = 1.000` as suspect.

    The default tolerance is half a unit in the last decimal place the record
    actually printed, so a value stated to three decimals is checked to three
    decimals. Demanding more precision than the notation claims would fail records
    that are correctly rounded.
    """

    match = _NOTATION_RE.match(text)
    if not match:
        raise ValueError(
            "expected notation like '1 MWh_e, fx = 1.0' or "
            "'1 MWh_th, fx = 0.170 [Th = 80 C, T0 = 20 C]'"
        )
    parsed = parse_energy_notation(text)
    stated_text = match.group("factor")
    if tolerance is None:
        tolerance = _printed_number_tolerance(stated_text)

    if parsed.sink_c is None:
        return NotationVerification(
            verifiable=False,
            agrees=False,
            stated_exergy_factor=parsed.exergy_factor,
            recomputed_exergy_factor=None,
            equation="",
            substitution="",
            difference=None,
            tolerance=tolerance,
            reason="the record declares no reference temperature T0",
        )

    sink_k = float(parsed.sink_c) + 273.15
    if "_solar" in parsed.unit.lower():
        recomputed = petela_exergy_factor(sink_k)
        equation = "fx = 1 - (4/3)(T0/Tsun) + (1/3)(T0/Tsun)^4"
        substitution = f"T0={sink_k:g} K, Tsun={T_SUN_K:g} K"
    elif parsed.source_c is not None and parsed.return_c is not None:
        recomputed = sensible_heat_exergy_factor_c(
            parsed.source_c,
            parsed.return_c,
            parsed.sink_c,
        )
        equation = "fx = 1 - T0 ln(Ts/Tr)/(Ts-Tr)"
        source_k = parsed.source_c + 273.15
        return_k = parsed.return_c + 273.15
        substitution = f"1 - {sink_k:g} ln({source_k:g}/{return_k:g})/({source_k:g}-{return_k:g})"
    elif parsed.source_c is not None:
        source_k = float(parsed.source_c) + 273.15
        recomputed = thermal_exergy_factor(source_k, sink_k)
        equation = "fx = 1 - T0/Th"
        substitution = f"1 - {sink_k:g}/{source_k:g}"
    elif parsed.cold_service_c is not None:
        cold_k = float(parsed.cold_service_c) + 273.15
        recomputed = cooling_exergy_factor_c(parsed.cold_service_c, parsed.sink_c)
        equation = "fx = T0/Tcold - 1"
        substitution = f"{sink_k:g}/{cold_k:g} - 1"
    else:
        return NotationVerification(
            verifiable=False,
            agrees=False,
            stated_exergy_factor=parsed.exergy_factor,
            recomputed_exergy_factor=None,
            equation="",
            substitution="",
            difference=None,
            tolerance=tolerance,
            reason="the record declares T0 but no source or cold-service temperature",
        )

    difference = abs(recomputed - parsed.exergy_factor)
    return NotationVerification(
        verifiable=True,
        agrees=difference <= tolerance,
        stated_exergy_factor=parsed.exergy_factor,
        recomputed_exergy_factor=recomputed,
        equation=equation,
        substitution=substitution,
        difference=difference,
        tolerance=tolerance,
    )


def report_from_notation(
    text: str,
    *,
    context: Optional[ReferenceContext] = None,
    label: Optional[str] = None,
) -> EnergyReport:
    """Build an EnergyReport from `1 MWh_th, fx = 0.730` style notation."""

    parsed = parse_energy_notation(text)
    return EnergyReport(
        quantity=parsed.quantity,
        unit=parsed.unit,
        exergy_factor=parsed.exergy_factor,
        context=context
        or ReferenceContext(
            reference="declared by reporter",
            boundary="declared by reporter",
            operating_basis="provided Exergy Factor",
        ),
        label=label,
    )


def thermal_exergy_factor(source_k: Number, sink_k: Number) -> float:
    """Carnot Exergy Factor for heat from a source to a sink, both in kelvin."""

    source = float(source_k)
    sink = float(sink_k)
    if not math.isfinite(source) or not math.isfinite(sink):
        raise ValueError("temperatures must be finite")
    if source <= 0 or sink <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if source < sink:
        raise ValueError("source temperature must be greater than or equal to sink temperature")
    if source == sink:
        return 0.0
    return 1.0 - sink / source


def thermal_exergy_factor_c(source_c: Number, sink_c: Number) -> float:
    """Carnot Exergy Factor for heat from a source to a sink, both in C."""

    return thermal_exergy_factor(float(source_c) + 273.15, float(sink_c) + 273.15)


def cooling_exergy_factor_c(cold_service_c: Number, ambient_sink_c: Number) -> float:
    """Minimum work potential per unit cooling for a cold service below ambient.

    This uses fx = T_ambient / T_cold - 1. Treat it as a service-demand factor,
    not as a heat-source factor.
    """

    cold = float(cold_service_c) + 273.15
    ambient = float(ambient_sink_c) + 273.15
    if not math.isfinite(cold) or not math.isfinite(ambient):
        raise ValueError("temperatures must be finite")
    if cold <= 0 or ambient <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if ambient < cold:
        raise ValueError("ambient sink must be warmer than or equal to the cold service")
    if ambient == cold:
        return 0.0
    return ambient / cold - 1.0


def sensible_heat_exergy_factor_c(
    supply_c: Number,
    return_c: Number,
    sink_c: Number,
) -> float:
    """Average Exergy Factor for sensible heat cooling from supply to return.

    This constant-heat-capacity integral is the F3 sensitivity model used by the
    canonical paper: ``1 - T0 * ln(Ts/Tr) / (Ts - Tr)``. Temperatures are supplied
    in degrees Celsius and converted to kelvin internally.
    """

    supply = float(supply_c) + 273.15
    return_temperature = float(return_c) + 273.15
    sink = float(sink_c) + 273.15
    if not all(math.isfinite(value) for value in (supply, return_temperature, sink)):
        raise ValueError("temperatures must be finite")
    if min(supply, return_temperature, sink) <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if supply <= return_temperature:
        raise ValueError("supply temperature must be greater than return temperature")
    logarithmic_mean = (supply - return_temperature) / math.log(supply / return_temperature)
    if logarithmic_mean < sink:
        raise ValueError(
            "the logarithmic-mean stream temperature must be greater than or equal to "
            "the reference sink"
        )
    if logarithmic_mean == sink:
        return 0.0
    return 1.0 - sink / logarithmic_mean


def petela_exergy_factor(reference_k: Number = STANDARD_AMBIENT_K) -> float:
    """Petela Exergy Factor for solar radiation against a reference environment."""

    reference = float(reference_k)
    _require_positive(reference, "reference_k")
    if reference > T_SUN_K:
        raise ValueError("reference_k must not exceed the solar source temperature")
    if reference == T_SUN_K:
        return 0.0
    ratio = reference / T_SUN_K
    return 1.0 - (4.0 / 3.0) * ratio + (1.0 / 3.0) * ratio**4


def solar_exergy_rate(
    irradiance_w_m2: Number,
    area_m2: Number,
    reference_k: Number = STANDARD_AMBIENT_K,
) -> float:
    """Solar exergy input rate in W_ex from irradiance and area."""

    irradiance = float(irradiance_w_m2)
    area = float(area_m2)
    _require_nonnegative(irradiance, "irradiance_w_m2")
    _require_nonnegative(area, "area_m2")
    return irradiance * area * petela_exergy_factor(reference_k)


def chemical_exergy_factor(chemical_exergy: Number, energy_basis: Number) -> float:
    """Return chemical Exergy Factor as chemical exergy divided by the declared energy basis."""

    exergy = float(chemical_exergy)
    basis = float(energy_basis)
    _require_positive(exergy, "chemical_exergy")
    _require_positive(basis, "energy_basis")
    return exergy / basis


WeightedInput = Union[
    EnergyReport,
    PowerReport,
    Mapping[str, Number],
    Tuple[Number, Number],
]


def weighted_exergy_factor(records: Iterable[WeightedInput]) -> float:
    """Energy-weighted or power-weighted average Exergy Factor.

    Each record may be an EnergyReport, PowerReport, mapping with
    `quantity` or `power` plus `exergy_factor`, or a `(quantity, factor)` tuple.
    """

    total_quantity = 0.0
    total_exergy = 0.0

    for record in records:
        quantity, factor = _quantity_and_factor(record)
        _require_nonnegative(quantity, "quantity")
        _require_valid_factor(factor)
        total_quantity += quantity
        total_exergy += quantity * factor

    if total_quantity <= 0:
        raise ValueError("at least one record with positive quantity or power is required")
    return total_exergy / total_quantity


def _quantity_and_factor(record: WeightedInput) -> Tuple[float, float]:
    if isinstance(record, EnergyReport):
        return record.quantity, record.exergy_factor
    if isinstance(record, PowerReport):
        return record.power, record.exergy_factor
    if isinstance(record, Mapping):
        if "quantity" in record:
            quantity = record["quantity"]
        elif "power" in record:
            quantity = record["power"]
        else:
            raise ValueError("mapping records must include quantity or power")
        return float(quantity), float(record["exergy_factor"])

    quantity, factor = record
    return float(quantity), float(factor)


def _require_nonnegative(value: Number, name: str) -> None:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")


def _require_positive(value: Number, name: str) -> None:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def _require_valid_factor(value: Number) -> None:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("exergy_factor must be a finite nonnegative number")


def _format_number(value: float, precision: int = 3) -> str:
    text = f"{value:.{precision}f}"
    compact = text.rstrip("0").rstrip(".")
    if value != 0 and float(compact or "0") == 0:
        return f"{value:.{precision}g}"
    return compact


def _printed_number_tolerance(text: str) -> float:
    """Half of the final printed place, including scientific notation."""

    mantissa, marker, exponent_text = text.lower().partition("e")
    decimals = len(mantissa.partition(".")[2])
    exponent = int(exponent_text) if marker else 0
    return 0.5 * (10.0 ** (exponent - decimals))
