import frappe


def execute():
	settings_meta = frappe.get_meta("Currency Exchange Settings")
	settings = frappe.get_doc("Currency Exchange Settings")

	if (
		"frankfurter.dev" not in settings_meta.get_options("service_provider").split("\n")
		or settings.service_provider != "frankfurter.app"
	):
		return

	settings.service_provider = "frankfurter.dev"
	settings.set_parameters_and_result()
	settings.flags.ignore_validate = True
	settings.save()
