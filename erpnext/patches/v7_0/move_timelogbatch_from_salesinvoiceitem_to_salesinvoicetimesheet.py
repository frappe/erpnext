import frappe

from erpnext.manufacturing.doctype.production_order.production_order import add_timesheet_detail

def execute():
	for si in frappe.db.sql(""" select sales_invoice as name from `tabTime Sheet`
		where sales_invoice is not null and docstatus < 2""", as_dict=True):
		si_doc = frappe.get_doc('Sales Invoice', si.name)
		for item in si_doc.items:
			if item.time_log_batch:
				ts = si_doc.append('timesheets',{})
				ts.time_sheet = item.time_log_batch
				ts.billing_amount = frappe.db.get_value('Time Log Batch', item.time_log_batch, 'total_billing_amount')
		si_doc.ignore_validate_update_after_submit = True
		si_doc.update_time_sheet(ts.time_sheet)
		si_doc.save()