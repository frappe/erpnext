from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('projects', 'doctype', 'task')
	frappe.reload_doc('projects', 'doctype', 'timesheet')
	if not frappe.db.table_exists("Time Log"):
		return

	from erpnext.manufacturing.doctype.work_order.work_order \
		import make_timesheet, add_timesheet_detail

	for data in frappe.db.sql("select * from `tabTime Log`", as_dict=1):
		if data.task:
			company = frappe.db.get_value("Task", data.task, "company")
		elif data.work_order:
			company = frappe.db.get_value("Work Order", data.work_order, "company")
		else:
			company = frappe.db.get_single_value('Global Defaults', 'default_company')
		
		time_sheet = make_timesheet(data.work_order, company)
		args = get_timelog_data(data)
		add_timesheet_detail(time_sheet, args)
		if data.docstatus == 2:
			time_sheet.docstatus = 0
		else:
			time_sheet.docstatus = data.docstatus
		time_sheet.employee = data.employee
		time_sheet.note = data.note
		time_sheet.company = company

		time_sheet.set_status()
		time_sheet.set_dates()
		time_sheet.update_cost()
		time_sheet.calculate_total_amounts()
		time_sheet.flags.ignore_validate = True
		time_sheet.flags.ignore_links = True
		time_sheet.save(ignore_permissions=True)

		# To ignore validate_mandatory_fields function
		if data.docstatus == 1:
			time_sheet.db_set("docstatus", 1)
			for d in time_sheet.get("time_logs"):
				d.db_set("docstatus", 1)
			time_sheet.update_work_order(time_sheet.name)
			time_sheet.update_task_and_project()
		if data.docstatus == 2:
			time_sheet.db_set("docstatus", 2)
			for d in time_sheet.get("time_logs"):
				d.db_set("docstatus", 2)

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
