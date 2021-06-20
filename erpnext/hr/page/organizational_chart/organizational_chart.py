from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_children(parent=None, company=None, is_root=False, is_tree=False, fields=None):

	filters = [['status', '!=', 'Left']]
	if company and company != 'All Companies':
		filters.append(['company', '=', company])

	if not fields:
		fields = ['employee_name', 'name', 'reports_to', 'image', 'designation']

	if is_root:
		parent = ''
	if parent and company and parent!=company:
		filters.append(['reports_to', '=', parent])
	else:
		filters.append(['reports_to', '=', ''])

	employees = frappe.get_list('Employee', fields=fields,
		filters=filters, order_by='name')

	for employee in employees:
		is_expandable = frappe.get_all('Employee', filters=[
			['reports_to', '=', employee.get('name')]
		])
		employee.connections = get_connections(employee.name)
		employee.expandable = 1 if is_expandable else 0

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