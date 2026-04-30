import frappe


def execute():
	try:
		from erpnext.patches.v16_0.update_currency_exchange_settings_for_frankfurter import execute

		execute()
	except ImportError:
		update_frankfurter_app_parameter_and_result()


def update_frankfurter_app_parameter_and_result():
	settings = frappe.get_doc("Currency Exchange Settings")
	if settings.service_provider != "frankfurter.app":
		return

	settings.set_parameters_and_result()
	settings.flags.ignore_validate = True
	settings.save()
