import frappe
from erpnext.accounts.doctype.bank_account.bank_account import is_valid_iban


def execute():
	"""
	Create Banks and Bank Accounts from bank details in Salary Slip.
	"""
	frappe.reload_doctype("Salary Slip")
	salary_slips = frappe.get_all("Salary Slip",
		fields=["name", "employee", "bank_account_no", "bank_name"]
	)

	for salary_slip in salary_slips:
		if not (salary_slip.bank_account_no and salary_slip.bank_name):
			continue

		existing_accounts = frappe.get_list("Bank Account",
			filters={
				"bank": salary_slip.bank_name
			},
			or_filters={
				"bank_account_no": salary_slip.bank_account_no,
				"iban": salary_slip.bank_account_no
			}
		)

		if existing_accounts:
			bank_account = existing_accounts[0].name
		else:
			if not frappe.db.exists("Bank", salary_slip.bank_name):
				new_bank = frappe.new_doc("Bank")
				new_bank.bank_name = salary_slip.bank_name
				new_bank.save()

			new_bank_account = frappe.new_doc("Bank Account")
			new_bank_account.account_name = salary_slip.bank_account_no

			if is_valid_iban(salary_slip.bank_account_no):
				new_bank_account.iban = salary_slip.bank_account_no
			else:
				new_bank_account.bank_account_no = salary_slip.bank_account_no

			new_bank_account.bank = salary_slip.bank_name
			new_bank_account.party_type = "Employee"
			new_bank_account.party = salary_slip.employee
			new_bank_account.save()
			bank_account = new_bank_account.name

		frappe.set_value("Salary Slip", salary_slip.name, "bank_account", bank_account)
