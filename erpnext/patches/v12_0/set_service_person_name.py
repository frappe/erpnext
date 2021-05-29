import frappe

def execute():
	doctypes = [
		'Quotation',
		'Sales Order',
		'Delivery Note',
		'Sales Invoice',
		'Project'
	]
	for dt in doctypes:
		frappe.db.sql("""
			update `tab{0}` p
			inner join `tabEmployee` e on e.name = p.service_advisor
			set p.service_advisor_name = e.employee_name
		""".format(dt))

		frappe.db.sql("""
			update `tab{0}` p
			inner join `tabEmployee` e on e.name = p.service_manager
			set p.service_manager_name = e.employee_name
		""".format(dt))
