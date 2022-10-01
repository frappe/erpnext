import frappe


@frappe.whitelist()
def get_children(parent=None, company=None, exclude_node=None):
	filters = [["status", "!=", "Left"]]
	if company and company != "All Companies":
		filters.append(["company", "=", company])

	if parent and company and parent != company:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	if exclude_node:
		filters.append(["name", "!=", exclude_node])

	employees = frappe.get_list(
		"Employee",
		fields=["employee_name as name", "name as id", "reports_to", "image", "designation as title"],
		filters=filters,
		order_by="name",
	)

	for employee in employees:
		is_expandable = frappe.db.count("Employee", filters={"reports_to": employee.get("id")})
		employee.connections = get_connections(employee.id)
		employee.expandable = 1 if is_expandable else 0

	return employees


def get_connections(employee):
	num_connections = 0

	nodes_to_expand = frappe.get_list("Employee", filters=[["reports_to", "=", employee]])
	num_connections += len(nodes_to_expand)

	while nodes_to_expand:
		parent = nodes_to_expand.pop(0)
		descendants = frappe.get_list("Employee", filters=[["reports_to", "=", parent.name]])
		num_connections += len(descendants)
		nodes_to_expand.extend(descendants)

	return num_connections
