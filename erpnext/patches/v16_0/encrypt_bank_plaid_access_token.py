import frappe
from frappe.utils.password import set_encrypted_password


def execute():
	"""Move Plaid access tokens to the password store."""
	for bank in frappe.get_all(
		"Bank", filters={"plaid_access_token": ("is", "set")}, fields=["name", "plaid_access_token"]
	):
		if set(bank.plaid_access_token) == {"*"}:
			continue

		set_encrypted_password("Bank", bank.name, bank.plaid_access_token, "plaid_access_token")
		frappe.db.set_value(
			"Bank", bank.name, "plaid_access_token", "*" * len(bank.plaid_access_token), update_modified=False
		)
