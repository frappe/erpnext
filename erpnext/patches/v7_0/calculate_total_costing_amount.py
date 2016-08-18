import frappe
from frappe.utils import flt

def execute():
	frappe.reload_doc('projects', 'doctype', 'timesheet')

	for data in frappe.get_all('Timesheet', fields=["name, total_costing_amount"],
		filters = [["docstatus", "<", "2"]]):
		if flt(data.total_costing_amount) == 0.0:
			ts = frappe.get_doc('Timesheet', data.name)
			ts.update_cost()
			ts.calculate_total_amounts()
			ts.flags.ignore_validate = True
			ts.flags.ignore_mandatory = True
			ts.flags.ignore_validate_update_after_submit = True
			ts.flags.ignore_links = True
			ts.save()
