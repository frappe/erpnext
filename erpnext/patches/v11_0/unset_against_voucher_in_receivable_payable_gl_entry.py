import frappe
import erpnext

def execute():
	doctypes = [
		('Sales Invoice', 'Customer'),
		('Purchase Invoice', 'Supplier'),
		('Fees', 'Student'),
		('Expense Claim', 'Employee')
	]

	for dt, party_type in doctypes:
		dr_or_cr = "debit - credit" if erpnext.get_party_account_type(party_type) == 'Receivable' else "credit - debit"
		frappe.db.sql("""
			update `tabGL Entry`
			set against_voucher = '', against_voucher_type = ''
			where voucher_type = '{dt}' and against_voucher_type = voucher_type and against_voucher = voucher_no
				and {dr_or_cr} > 0
		""".format(dt=dt, dr_or_cr=dr_or_cr))
