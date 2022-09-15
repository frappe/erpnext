import frappe
from frappe.geo.country_info import get_country_timezone_info
from frappe.translate import set_default_language


@frappe.whitelist()
def get_onboarding_data():
	workspaces_to_ignore = ["Home", "Build", "ERPNext Settings", "Users"]
	workspaces = frappe.get_all(
		"Workspace",
		filters={"name": ("not in", workspaces_to_ignore)},
		fields=["name", "title", "module", "icon", "description"],
		order_by="sequence_id",
	)

	regional_data = get_country_timezone_info()

	return {"workspaces": workspaces, "regional_data": regional_data, "language": frappe.local.lang}


@frappe.whitelist()
def load_messages(language):
	"""Load translation messages for given language from all `setup_wizard_requires`
	javascript files"""
	frappe.clear_cache()
	set_default_language(language)
	frappe.db.commit()

	return frappe.local.lang
