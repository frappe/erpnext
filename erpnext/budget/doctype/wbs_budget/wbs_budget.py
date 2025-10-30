# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WBSBudget(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:  # pragma: no cover
		from erpnext.budget.doctype.budget_account.budget_account import BudgetAccount
		from erpnext.budget.doctype.wbs_budget_items.wbs_budget_items import WBSBudgetItems
		from frappe.types import DF

		accounts: DF.Table[BudgetAccount]
		action_if_accumulated_monthly_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		amended_from: DF.Link | None
		applicable_on_booking_actual_expenses: DF.Check
		applicable_on_material_request: DF.Check
		applicable_on_purchase_order: DF.Check
		available_budget: DF.Currency
		budget_against: DF.Literal["", "Cost Center", "Project"]
		company: DF.Link | None
		cost_center: DF.Link | None
		fiscal_year: DF.Link | None
		from_date: DF.Date | None
		monthly_distribution: DF.Link | None
		project: DF.Link | None
		to_date: DF.Date | None
		total_amount: DF.Float
		wbs: DF.Link | None
		wbs_budget_items: DF.Table[WBSBudgetItems]
	# end: auto-generated types
	pass
