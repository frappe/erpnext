import math

import frappe
from frappe import _


def _excel_if(condition, true_value, false_value):
	return true_value if condition else false_value


def _round_up(number, digits=0):
	factor = 10**digits
	return math.ceil(number * factor) / factor


def _round_down(number, digits=0):
	factor = 10**digits
	return math.floor(number * factor) / factor


def _ceiling(number, significance=1):
	return math.ceil(number / significance) * significance


def _floor(number, significance=1):
	return math.floor(number / significance) * significance


FORMULA_FUNCTIONS = {
	"IF": _excel_if,
	"AND": lambda *args: all(args),
	"OR": lambda *args: any(args),
	"NOT": lambda value: not value,
	"MIN": min,
	"MAX": max,
	"SUM": lambda *args: sum(args),
	"ABS": abs,
	"ROUND": round,
	"ROUNDUP": _round_up,
	"ROUNDDOWN": _round_down,
	"CEILING": _ceiling,
	"FLOOR": _floor,
	"INT": lambda number: math.floor(number),
	"MOD": lambda number, divisor: number % divisor,
	"SQRT": math.sqrt,
	"POWER": lambda base, exponent: base**exponent,
}


def function_namespace() -> dict:
	return dict(FORMULA_FUNCTIONS)


def evaluate(expression: str | None, context: dict) -> dict:
	if not expression or not expression.strip():
		return {"ok": True, "value": None}
	try:
		value = frappe.safe_eval(expression, eval_globals=None, eval_locals=context)
		return {"ok": True, "value": value}
	except Exception as exception:
		return {"ok": False, "error": str(exception)}


def build_context(values: dict, variables: list | None = None) -> dict:
	context = function_namespace()
	context.update(values)
	for variable in variables or []:
		result = evaluate(variable.get("formula"), context)
		if not result["ok"]:
			frappe.throw(
				_("Formula for variable {0} failed: {1}").format(
					variable.get("variable_name"), result["error"]
				)
			)
		context[variable.get("variable_name")] = result["value"]
	return context
