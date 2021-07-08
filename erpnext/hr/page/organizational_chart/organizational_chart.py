from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_children(parent=None, company=None):

	filters = [['status', '!=', 'Left']]
	if company and company != 'All Companies':
		filters.append(['company', '=', company])

	if parent and company and parent != company:
		filters.append(['reports_to', '=', parent])
	else:
		filters.append(['reports_to', '=', ''])

	employees = frappe.get_list('Employee',
		fields=['employee_name as name', 'name as id', 'reports_to', 'image', 'designation as title'],
		filters=filters,
		order_by='name'
	)

	for employee in employees:
		is_expandable = frappe.db.count('Employee', filters={'reports_to': employee.get('id')})
		employee.connections = get_connections(employee.id)
		employee.expandable = 1 if is_expandable else 0

	employees.sort(key=lambda x: x['connections'], reverse=True)
	return employees


def get_connections(employee):
	num_connections = 0

	connections = frappe.get_list('Employee', filters=[
			['reports_to', '=', employee]
		])
	num_connections += len(connections)

	while connections:
		for entry in connections:
			connections = frappe.get_list('Employee', filters=[
				['reports_to', '=', entry.name]
			])
			num_connections += len(connections)

	return num_connections