"""
Life Sciences and Laboratory Calculation Tools.
Provides scientific calculations for dilution (C1V1 = C2V2), molarity,
and spectrophotometric nucleic acid purity (A260/A280).
"""
from typing import Dict, Any, Optional
from app.tools.base import BaseTool, ToolResult


class DilutionCalculatorTool(BaseTool):
    name = "dilution_calculator"
    description = "Calculates stock and target volumes or concentrations using C1V1 = C2V2 formula."
    parameters_schema = {
        "c1": {"type": "number", "description": "Stock concentration (C1)"},
        "v1": {"type": "number", "description": "Stock volume (V1) - optional if solving for V1"},
        "c2": {"type": "number", "description": "Desired target concentration (C2)"},
        "v2": {"type": "number", "description": "Desired target final volume (V2)"},
        "unit_conc": {"type": "string", "description": "Concentration unit (e.g. mM, M, ug/mL, X)"},
        "unit_vol": {"type": "string", "description": "Volume unit (e.g. mL, uL, L)"},
    }

    def execute(
        self,
        c1: Optional[float] = None,
        v1: Optional[float] = None,
        c2: Optional[float] = None,
        v2: Optional[float] = None,
        unit_conc: str = "mM",
        unit_vol: str = "mL",
        **kwargs,
    ) -> ToolResult:
        try:
            # Solve for V1: V1 = (C2 * V2) / C1
            if v1 is None and c1 and c2 and v2:
                if c1 <= 0:
                    return ToolResult(success=False, error="C1 must be greater than 0")
                calc_v1 = (c2 * v2) / c1
                buffer_vol = v2 - calc_v1
                msg = (
                    f"To prepare {v2} {unit_vol} of {c2} {unit_conc} solution: "
                    f"pipette {calc_v1:.3f} {unit_vol} of stock ({c1} {unit_conc}) "
                    f"and bring up volume with {buffer_vol:.3f} {unit_vol} of diluent/buffer."
                )
                return ToolResult(
                    success=True,
                    data={"v1": round(calc_v1, 4), "buffer_volume": round(buffer_vol, 4), "v2": v2, "c2": c2},
                    message=msg,
                )

            # Solve for C2: C2 = (C1 * V1) / V2
            elif c2 is None and c1 and v1 and v2:
                if v2 <= 0:
                    return ToolResult(success=False, error="V2 must be greater than 0")
                calc_c2 = (c1 * v1) / v2
                msg = f"The resulting diluted concentration (C2) will be {calc_c2:.4f} {unit_conc}."
                return ToolResult(success=True, data={"c2": round(calc_c2, 4)}, message=msg)

            return ToolResult(
                success=False,
                error="Insufficient parameters. Please provide c1, c2, and v2 to solve for stock volume v1.",
                message="Please specify stock concentration (C1), target concentration (C2), and target volume (V2).",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"Dilution calculation error: {e}")


class MolarityCalculatorTool(BaseTool):
    name = "molarity_calculator"
    description = "Calculates mass needed to prepare a solution: Mass (g) = Molarity (mol/L) * Volume (L) * Molecular Weight (g/mol)."
    parameters_schema = {
        "molarity": {"type": "number", "description": "Desired molarity in M or mM"},
        "volume_ml": {"type": "number", "description": "Desired volume in milliliters (mL)"},
        "molecular_weight": {"type": "number", "description": "Molecular weight (g/mol)"},
    }

    def execute(
        self,
        molarity: float,
        volume_ml: float,
        molecular_weight: float,
        is_millimolar: bool = False,
        **kwargs,
    ) -> ToolResult:
        try:
            vol_liters = volume_ml / 1000.0
            actual_m = molarity / 1000.0 if is_millimolar else molarity
            mass_grams = actual_m * vol_liters * molecular_weight

            if mass_grams < 0.001:
                disp_mass = f"{mass_grams * 1000000:.2f} µg"
            elif mass_grams < 1.0:
                disp_mass = f"{mass_grams * 1000:.2f} mg"
            else:
                disp_mass = f"{mass_grams:.4f} g"

            conc_disp = f"{molarity} mM" if is_millimolar else f"{molarity} M"
            msg = (
                f"Weigh out {disp_mass} of compound (MW: {molecular_weight} g/mol) "
                f"and dissolve in liquid up to {volume_ml} mL for a final {conc_disp} solution."
            )
            return ToolResult(
                success=True,
                data={"mass_grams": round(mass_grams, 6), "disp_mass": disp_mass, "volume_ml": volume_ml},
                message=msg,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"Molarity calculation error: {e}")

