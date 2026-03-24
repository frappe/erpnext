import frappe


def execute():
	for user in frappe.get_all("User", fields=["name", "home_settings"]):
		if user.home_settings and "Accounting" in user.home_settings:
			frappe.db.set_value(
				"User",
				user.name,
				"home_settings",
				user.home_settings.replace("Accounting", "Accounts"),
				update_modified=False,
			)
	frappe.cache().delete_key("home_settings")
