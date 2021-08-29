import frappe

from erpnext import get_region
from erpnext.accounts.doctype.bank_account.bank_account import is_valid_iban


def execute():
	"""
	Create Banks and Bank Accounts from bank details in Employee.
	"""
	frappe.reload_doctype("Employee")
	employees = frappe.get_all("Employee",
		fields=["name", "bank_name", "bank_ac_no"],
		filters={"bank_ac_no": ("is", "set"), "bank_name": ("is", "set")}
	)

	for employee in employees:
		existing_accounts = frappe.get_list("Bank Account", 
			filters={
				"bank": employee.bank_name
			},
			or_filters={
				"bank_account_no": employee.bank_ac_no,
				"iban": employee.bank_ac_no
			}
		)

		if existing_accounts:
			bank_account = existing_accounts[0].name
		else:
			if not frappe.db.exists("Bank", employee.bank_name):
				new_bank = frappe.new_doc("Bank")
				new_bank.bank_name = employee.bank_name
				new_bank.save()

			new_bank_account = frappe.new_doc("Bank Account")
			new_bank_account.account_name = employee.bank_ac_no

			if is_valid_iban(employee.bank_ac_no):
				new_bank_account.iban = employee.bank_ac_no
			else:
				new_bank_account.bank_account_no = employee.bank_ac_no

			new_bank_account.bank = employee.bank_name
			new_bank_account.party_type = "Employee"
			new_bank_account.party = employee.name

			if get_region() == "India":
				new_bank_account.ifsc_code = employee.ifsc_code
				new_bank_account.micr_code = employee.micr_code

			new_bank_account.save()
			bank_account = new_bank_account.name

		frappe.set_value("Employee", employee.name, "bank_account", bank_account)
