import frappe


def execute():
	settings = frappe.get_doc("Currency Exchange Settings")
	if settings.service_provider != "frankfurter.app":
		return

	settings.service_provider = "frankfurter.dev"
	settings.set_parameters_and_result()
	settings.flags.ignore_validate = True
	settings.save()
