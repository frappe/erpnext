from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "employee")
	if not frappe.db.has_column("Employee", "bank_name"):
		return

	existing_banks = {bank.name.lower(): bank.name for bank in frappe.get_all("Bank")}
	for employee in frappe.get_all("Employee", fields=['name', 'bank_name'],
			filters={"bank_name": ("!=", "")}):
		bank_name_lower = employee.bank_name.lower()
		if bank_name_lower not in existing_banks:
			bank = frappe.new_doc("Bank")
			bank.bank_name = employee.bank_name
			bank.save()
			existing_banks[bank_name_lower] = employee.bank_name

		frappe.db.set_value("Employee", employee.name, "bank", existing_banks[bank_name_lower])