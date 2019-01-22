import frappe

def execute():
	frappe.reload_doctype('Employee')
	frappe.db.sql('update tabEmployee set first_name = employee_name')

	# update holiday list
	frappe.reload_doctype('Holiday List')
	for holiday_list in frappe.get_all('Holiday List'):
		holiday_list = frappe.get_doc('Holiday List', holiday_list.name)
		holiday_list.db_set('total_holidays', len(holiday_list.holidays), update_modified = False)

