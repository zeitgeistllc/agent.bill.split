# tools/bill_calculator.py
# This tool performs the precise mathematical calculations. No LLM involved.

from langchain.tools import tool
from typing import TypedDict, Optional

class BillSplit(TypedDict):
    """Data model for the output of the calculator."""
    apt1_fixed_fee: float
    apt1_consumption_cost: float
    apt1_total: float
    apt2_fixed_fee: float
    apt2_consumption_cost: float
    apt2_total: float
    total_check: float

@tool
def bill_calculator_tool(
    total_amount: float,
    total_consumption: float,
    apt1_consumption: float,
    fixed_fees: Optional[float] = 0.0
) -> BillSplit:
    """
    Calculates the split for electricity or water bills.
    This tool takes the total bill amount, total consumption (in kWh or m³),
    apartment 1's specific consumption, and any fixed fees.
    It splits fixed fees 50/50 and consumption costs proportionally.
    It returns a dictionary with the detailed split for each apartment.
    """
    if fixed_fees > total_amount:
        return "Error: Fixed fees cannot be greater than the total amount."
    if apt1_consumption > total_consumption:
        return "Error: Apartment 1 consumption cannot be greater than total consumption."

    consumption_cost = total_amount - fixed_fees
    cost_per_unit = consumption_cost / total_consumption if total_consumption > 0 else 0

    apt1_fixed = fixed_fees / 2
    apt2_fixed = fixed_fees / 2

    apt1_consump_cost = apt1_consumption * cost_per_unit
    apt2_consumption = total_consumption - apt1_consumption
    apt2_consump_cost = apt2_consumption * cost_per_unit

    apt1_total = apt1_fixed + apt1_consump_cost
    apt2_total = apt2_fixed + apt2_consump_cost

    return {
        "apt1_fixed_fee": round(apt1_fixed, 2),
        "apt1_consumption_cost": round(apt1_consump_cost, 2),
        "apt1_total": round(apt1_total, 2),
        "apt2_fixed_fee": round(apt2_fixed, 2),
        "apt2_consumption_cost": round(apt2_consump_cost, 2),
        "apt2_total": round(apt2_total, 2),
        "total_check": round(apt1_total + apt2_total, 2)
    }

@tool
def arnona_calculator_tool(total_amount: float) -> dict:
    """Calculates the 50/50 split for Arnona (property tax)."""
    split_amount = total_amount / 2
    return {
        "apt1_total": round(split_amount, 2),
        "apt2_total": round(split_amount, 2),
    }

