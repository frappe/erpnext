import frappe

from erpnext.manufacturing.doctype.production_order.production_order import make_time_sheet, add_timesheet_detail

def execute():	
	for data in frappe.get_all('Time Log', fields=["*"],
		filters = [["docstatus", "<", "2"]]):
		time_sheet = make_time_sheet(data.production_order)
		args = get_timesheet_data(data)
		add_timesheet_detail(time_sheet, args)
		time_sheet.docstatus = data.docstatus
		time_sheet.company = frappe.db.get_single_value('Global Defaults', 'default_company')
		time_sheet.save(ignore_permissions=True)

def get_timesheet_data(data):
	return {
		'from_time': data.from_time,
		'hours': data.hours,
		'to_time': data.to_time,
		'project': data.project,
		'activity_type': data.activity_type or "Planning",
		'operation': data.operation,
		'operation_id': data.operation_id,
		'workstation': data.workstation,
		'completed_qty': data.completed_qty
	}