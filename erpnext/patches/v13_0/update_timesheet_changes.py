import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("projects", "doctype", "timesheet")
	frappe.reload_doc("projects", "doctype", "timesheet_detail")

	if frappe.db.has_column("Timesheet Detail", "billable"):
		rename_field("Timesheet Detail", "billable", "is_billable")

	base_currency = frappe.defaults.get_global_default("currency")
	timesheet_detail = frappe.qb.DocType("Timesheet Detail")
	timesheet = frappe.qb.DocType("Timesheet")

	(
		frappe.qb.update(timesheet_detail)
		.set(timesheet_detail.base_billing_rate, timesheet_detail.billing_rate)
		.set(timesheet_detail.base_billing_amount, timesheet_detail.billing_amount)
		.set(timesheet_detail.base_costing_rate, timesheet_detail.costing_rate)
		.set(timesheet_detail.base_costing_amount, timesheet_detail.costing_amount)
	).run()

	(
		frappe.qb.update(timesheet)
		.set(timesheet.currency, base_currency)
		.set(timesheet.exchange_rate, 1.0)
		.set(timesheet.base_total_billable_amount, timesheet.total_billable_amount)
		.set(timesheet.base_total_billed_amount, timesheet.total_billed_amount)
		.set(timesheet.base_total_costing_amount, timesheet.total_costing_amount)
	).run()
