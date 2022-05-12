import frappe


def execute():
	frappe.reload_doc("payroll", "doctype", "employee_cost_center")
	frappe.reload_doc("payroll", "doctype", "salary_structure_assignment")

	employees = frappe.get_all("Employee", fields=["department", "payroll_cost_center", "name"])

	employee_cost_center = {}
	for d in employees:
		cost_center = d.payroll_cost_center
		if not cost_center and d.department:
			cost_center = frappe.get_cached_value("Department", d.department, "payroll_cost_center")

		if cost_center:
			employee_cost_center.setdefault(d.name, cost_center)

	salary_structure_assignments = frappe.get_all(
		"Salary Structure Assignment", filters={"docstatus": ["!=", 2]}, fields=["name", "employee"]
	)

	for d in salary_structure_assignments:
		cost_center = employee_cost_center.get(d.employee)
		if cost_center:
			assignment = frappe.get_doc("Salary Structure Assignment", d.name)
			if not assignment.get("payroll_cost_centers"):
				assignment.append("payroll_cost_centers", {"cost_center": cost_center, "percentage": 100})
				assignment.save()
