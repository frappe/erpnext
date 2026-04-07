import frappe
from frappe.utils import date_diff, getdate, today


def execute():
	steps = frappe.get_all(
		"Onboarding Step",
		filters={"is_complete": 0},
		fields=["name", "action", "reference_document"],
	)

	if not steps:
		return

	company_creation = frappe.get_all("Company", fields=["creation"], order_by="creation asc", limit=1)
	if not company_creation:
		return

	days_diff = date_diff(getdate(today()), getdate(company_creation[0].creation))

	if days_diff > 15:
		complete_all_onboarding_steps(steps)
	else:
		complete_onboarding_steps_if_record_exists(steps)


def complete_all_onboarding_steps(steps):
	for step in steps:
		frappe.db.set_value("Onboarding Step", step.name, "is_complete", 1, update_modified=False)


def complete_onboarding_steps_if_record_exists(steps):
	for step in steps:
		if (
			step.action == "Create Entry"
			and step.reference_document
			and frappe.get_all(step.reference_document, limit=1)
		):
			frappe.db.set_value("Onboarding Step", step.name, "is_complete", 1, update_modified=False)
