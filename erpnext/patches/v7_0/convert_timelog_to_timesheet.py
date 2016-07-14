import frappe

from erpnext.manufacturing.doctype.production_order.production_order import make_timesheet, add_timesheet_detail

def execute():
	frappe.reload_doc('projects', 'doctype', 'timesheet')

	for data in frappe.get_all('Time Log', fields=["*"],
		filters = [["docstatus", "<", "2"]]):
		time_sheet = make_timesheet(data.production_order)
		args = get_timelog_data(data)
		add_timesheet_detail(time_sheet, args)
		time_sheet.docstatus = data.docstatus
		time_sheet.note = data.note
		time_sheet.company = frappe.db.get_single_value('Global Defaults', 'default_company')
		time_sheet.save(ignore_permissions=True)

def get_timelog_data(data):
	return {
		'billable': data.billable,
		'from_time': data.from_time,
		'hours': data.hours,
		'to_time': data.to_time,
		'project': data.project,
		'task': data.task,
		'activity_type': data.activity_type,
		'operation': data.operation,
		'operation_id': data.operation_id,
		'workstation': data.workstation,
		'completed_qty': data.completed_qty,
		'billing_rate': data.billing_rate,
		'billing_amount': data.billing_amount,
		'costing_rate': data.costing_rate,
		'costing_amount': data.costing_amount
	}
