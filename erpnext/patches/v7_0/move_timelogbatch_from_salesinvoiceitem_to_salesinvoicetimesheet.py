import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_payment')
	for time_sheet in frappe.db.sql(""" select sales_invoice, name, total_billing_amount from `tabTimesheet`
		where sales_invoice is not null and docstatus < 2""", as_dict=True):
		si_doc = frappe.get_doc('Sales Invoice', time_sheet.sales_invoice)
		ts = si_doc.append('timesheets',{})
		ts.time_sheet = time_sheet.name
		ts.billing_amount = time_sheet.total_billing_amount
		si_doc.update_time_sheet(time_sheet.sales_invoice)
		si_doc.flags.ignore_validate_update_after_submit = True
		si_doc.save()