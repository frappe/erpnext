import frappe
from frappe.utils.password import set_encrypted_password

from erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings import remove_access_key

DOCTYPE = "Currency Exchange Settings"


def execute():
	"""Move the access key to the password store and drop its plain-text copies."""
	access_key = frappe.db.get_single_value(DOCTYPE, "access_key")
	if access_key and set(access_key) != {"*"}:
		set_encrypted_password(DOCTYPE, DOCTYPE, access_key, "access_key")
		frappe.db.set_single_value(DOCTYPE, "access_key", "*" * len(access_key))

	# a custom provider's parameters are set by the user, so only the generated ones are dropped
	if frappe.db.get_single_value(DOCTYPE, "service_provider") == "exchangerate.host":
		frappe.db.delete("Currency Exchange Settings Details", {"parent": DOCTYPE, "key": "access_key"})
		if url := frappe.db.get_single_value(DOCTYPE, "url"):
			frappe.db.set_single_value(DOCTYPE, "url", remove_access_key(url))

	frappe.clear_document_cache(DOCTYPE, DOCTYPE)
