# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

# Where a Budget checks spend, as ERPNext's budget controller (`BudgetValidation`) does: the field
# that turns the check on, then the fields holding what happens once the annual budget, or the
# monthly distribution accumulated to date, is exceeded there. Orders come first: they are what a
# budget most often holds back.
CONTROL_STAGES = (
	(
		"Purchase Order",
		"applicable_on_purchase_order",
		"action_if_annual_budget_exceeded_on_po",
		"action_if_accumulated_monthly_budget_exceeded_on_po",
	),
	(
		"Material Request",
		"applicable_on_material_request",
		"action_if_annual_budget_exceeded_on_mr",
		"action_if_accumulated_monthly_budget_exceeded_on_mr",
	),
	(
		"Expense",
		"applicable_on_booking_actual_expenses",
		"action_if_annual_budget_exceeded",
		"action_if_accumulated_monthly_budget_exceeded",
	),
	(
		"Cumulative",
		"applicable_on_cumulative_expense",
		"action_if_annual_exceeded_on_cumulative_expense",
		"action_if_accumulated_monthly_exceeded_on_cumulative_expense",
	),
)
BUDGET_FIELDS = ["name", "account", "budget_amount", "budget_start_date", "budget_end_date"] + [
	field for stage in CONTROL_STAGES for field in stage[1:]
]


def budget_summary(budget: dict, spend: dict[str, float]) -> dict:
	"""A Budget's amount, how it is enforced, and what its whole period has spent and has left after
	open orders and requests, for its account's row."""
	control = budget_control(budget)
	amount = flt(budget["budget_amount"])
	return {
		"amount": amount,
		"control": control,
		"rule": rule_label(control),
		"spent": spend["spent"],
		"available": amount - spend["spent"] - spend["ordered"] - spend["requested"],
	}


def rule_label(control: dict | None) -> str:
	"""A Budget's strongest rule as the Costing and Budgets tabs show it, such as "Stops on orders"."""
	if not control:
		return _("Tracks only")
	labels = {
		("Stop", "Purchase Order"): _("Stops on orders"),
		("Stop", "Material Request"): _("Stops on requests"),
		("Stop", "Expense"): _("Stops on expenses"),
		("Stop", "Cumulative"): _("Stops on total spend"),
		("Warn", "Purchase Order"): _("Warns on orders"),
		("Warn", "Material Request"): _("Warns on requests"),
		("Warn", "Expense"): _("Warns on expenses"),
		("Warn", "Cumulative"): _("Warns on total spend"),
	}
	return labels[(control["action"], control["stage"])]


def budget_control(budget: dict) -> dict | None:
	"""The Budget's strongest rule, to name it by: a stop before a warning, then orders before
	requests before expenses before total spend. None when it only tracks."""
	actions = stage_actions(budget)
	for wanted in ("Stop", "Warn"):
		for stage, _period, action in actions:
			if action == wanted:
				return {"stage": stage, "action": action}
	return None


def stage_actions(budget: dict) -> list[tuple[str, str, str]]:
	"""What the Budget does at each stage it checks, once exceeded: (stage, period, action), where
	the period is "annual" or "monthly"."""
	return [
		(stage, period, budget[field])
		for stage, applies, annual, monthly in CONTROL_STAGES
		if budget[applies]
		for period, field in (("annual", annual), ("monthly", monthly))
	]


def account_status(budget: dict | None, spend: dict[str, float]) -> str:
	"""How an account stands, as ERPNext's budget controller would judge a new order, request or
	expense on it today.

	`spend` holds the fiscal year's actual, ordered and requested amounts, and what the Budget's whole
	period has spent (`spent`) and spent to the end of this month (`spent_to_date`). Each stage the
	Budget checks compares its own amount (the cumulative stage, all three) with the budget amount and
	with the monthly distribution accumulated to today. A Stop on any check that is exceeded stops
	every new order, request and expense on the account.

	none: no budget; blocked: an exceeded check stops; over: an annual check is exceeded;
	over_to_date: only a monthly one is; ok otherwise.
	"""
	if not budget:
		return "none"
	exceeded = exceeded_checks(budget, spend)
	if any(action == "Stop" for _period, action in exceeded):
		return "blocked"
	if any(period == "annual" for period, _action in exceeded):
		return "over"
	return "over_to_date" if exceeded else "ok"


def exceeded_checks(budget: dict, spend: dict[str, float]) -> list[tuple[str, str]]:
	"""The (period, action) of each check the account is past."""
	amounts = {
		"Purchase Order": spend["ordered"],
		"Material Request": spend["requested"],
		"Cumulative": spend["ordered"] + spend["requested"] + spend["actual"],
	}
	# Orders, requests and total spend count one fiscal year, as `BudgetValidation` does. An expense
	# is also checked on every ledger entry by `validate_expense_against_budget`, which counts the
	# Budget's whole period, so that is the stricter measure of the two.
	expense = {"annual": spend["spent"], "monthly": spend["spent_to_date"]}
	limits = {"annual": flt(budget["budget_amount"]), "monthly": monthly_budget_to_date(budget)}
	precision = frappe.get_precision("Budget", "budget_amount")
	return [
		(period, action)
		for stage, period, action in stage_actions(budget)
		if flt((expense[period] if stage == "Expense" else amounts[stage]) - limits[period], precision) > 0
	]


def monthly_budget_to_date(budget: dict) -> float:
	"""The Budget's distribution accumulated from its first month to this one."""
	this_month = str(getdate())[:7]
	return sum(amount for month, amount in budget["by_month"].items() if month <= this_month)
