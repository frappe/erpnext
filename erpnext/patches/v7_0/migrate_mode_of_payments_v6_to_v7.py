from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_timesheet')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_payment')
	
	for data in frappe.db.sql("""select name, mode_of_payment, cash_bank_account, paid_amount, company 
		from `tabSales Invoice` 
		where is_pos = 1 and docstatus < 2 
		and cash_bank_account is not null and cash_bank_account != ''""", as_dict=1):
		
		if not data.mode_of_payment and not frappe.db.exists("Mode of Payment", "Cash"):
			mop = frappe.new_doc("Mode of Payment")
			mop.mode_of_payment = "Cash"
			mop.type = "Cash"
			mop.save()
		
		si_doc = frappe.get_doc('Sales Invoice', data.name)
		si_doc.append('payments', {
			'mode_of_payment': data.mode_of_payment or 'Cash',
			'account': data.cash_bank_account,
			'type': frappe.db.get_value('Mode of Payment', data.mode_of_payment, 'type') or 'Cash',
			'amount': data.paid_amount
		})

		si_doc.set_paid_amount()
		si_doc.flags.ignore_validate_update_after_submit = True
		si_doc.save()