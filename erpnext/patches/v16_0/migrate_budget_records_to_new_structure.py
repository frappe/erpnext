import frappe
from frappe.utils import add_months, flt, get_first_day, get_last_day


def execute():
	remove_old_property_setter()

	budget_names = frappe.db.get_list(
		"Budget",
		filters={"docstatus": ["in", [0, 1]]},
		pluck="name",
	)

	for budget in budget_names:
		migrate_single_budget(budget)


def remove_old_property_setter():
	old_property_setter = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": "Budget",
			"field_name": "naming_series",
			"property": "options",
			"value": "Budget-.YYYY.-",
		},
		"name",
	)

	if old_property_setter:
		frappe.delete_doc("Property Setter", old_property_setter, force=1)


def migrate_single_budget(budget_name):
	budget_doc = frappe.get_doc("Budget", budget_name)

	account_rows = frappe.get_all(
		"Budget Account",
		filters={"parent": budget_name},
		fields=["account", "budget_amount"],
		order_by="idx asc",
	)

	if not account_rows:
		return

	frappe.db.delete("Budget Account", filters={"parent": budget_doc.name})

	percentage_allocations = get_percentage_allocations(budget_doc)

	fiscal_year = frappe.get_cached_value(
		"Fiscal Year",
		budget_doc.fiscal_year,
		["name", "year_start_date", "year_end_date"],
		as_dict=True,
	)

	for row in account_rows:
		create_new_budget_from_row(budget_doc, fiscal_year, row, percentage_allocations)

	if budget_doc.docstatus == 1:
		budget_doc.cancel()
	else:
		frappe.delete_doc("Budget", budget_name)


def get_percentage_allocations(budget_doc):
	if budget_doc.monthly_distribution:
		distribution_doc = frappe.get_cached_doc("Monthly Distribution", budget_doc.monthly_distribution)
		return [flt(row.percentage_allocation) for row in distribution_doc.percentages]

	return [100 / 12] * 12


def create_new_budget_from_row(budget_doc, fiscal_year, account_row, percentage_allocations):
	new_budget = frappe.new_doc("Budget")

	core_fields = ["budget_against", "company", "cost_center", "project"]
	for field in core_fields:
		new_budget.set(field, budget_doc.get(field))

	new_budget.from_fiscal_year = fiscal_year.name
	new_budget.to_fiscal_year = fiscal_year.name
	new_budget.budget_start_date = fiscal_year.year_start_date
	new_budget.budget_end_date = fiscal_year.year_end_date

	new_budget.account = account_row.account
	new_budget.budget_amount = flt(account_row.budget_amount)
	new_budget.distribution_frequency = "Monthly"
	new_budget.distribute_equally = 1 if len(set(percentage_allocations)) == 1 else 0

	copy_fields = [
		"applicable_on_material_request",
		"action_if_annual_budget_exceeded_on_mr",
		"action_if_accumulated_monthly_budget_exceeded_on_mr",
		"applicable_on_purchase_order",
		"action_if_annual_budget_exceeded_on_po",
		"action_if_accumulated_monthly_budget_exceeded_on_po",
		"applicable_on_booking_actual_expenses",
		"action_if_annual_budget_exceeded",
		"action_if_accumulated_monthly_budget_exceeded",
		"applicable_on_cumulative_expense",
		"action_if_annual_exceeded_on_cumulative_expense",
		"action_if_accumulated_monthly_exceeded_on_cumulative_expense",
	]

	for field in copy_fields:
		new_budget.set(field, budget_doc.get(field))

	current_start = fiscal_year.year_start_date
	for percentage in percentage_allocations:
		new_budget.append(
			"budget_distribution",
			{
				"start_date": get_first_day(current_start),
				"end_date": get_last_day(current_start),
				"percent": percentage,
				"amount": new_budget.budget_amount * percentage / 100,
			},
		)
		current_start = add_months(current_start, 1)

	new_budget.flags.ignore_validate = True
	new_budget.flags.ignore_links = True
	new_budget.insert(ignore_permissions=True, ignore_mandatory=True)

	if budget_doc.docstatus == 1:
		new_budget.submit()
