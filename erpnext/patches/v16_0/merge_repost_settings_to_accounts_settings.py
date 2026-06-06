import frappe


def execute():
	if allowed := frappe.get_hooks("repost_allowed_doctypes"):
		accounts_settings = frappe.get_doc("Accounts Settings")
		for x in allowed:
			if x not in [t.document_type for t in accounts_settings.repost_allowed_types]:
				accounts_settings.append("repost_allowed_types", {"document_type": x})
		accounts_settings.save()
