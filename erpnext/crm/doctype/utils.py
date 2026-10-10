import frappe


def get_last_issue_from_customer(customer_name):
	issues = frappe.get_all(
		"Issue",
		{"customer": customer_name},
		["name", "subject", "customer"],
		order_by="creation desc",
		limit=1,
	)

	return issues[0] if issues else None


def get_scheduled_employees_for_popup(communication_medium):
	if not communication_medium:
		return []

	now_time = frappe.utils.nowtime()
	weekday = frappe.utils.get_weekday()

	available_employee_groups = frappe.get_all(
		"Communication Medium Timeslot",
		filters={
			"day_of_week": weekday,
			"parent": communication_medium,
			"from_time": ["<=", now_time],
			"to_time": [">=", now_time],
		},
		fields=["employee_group"],
	)

	if not available_employee_groups:
		return set()

	member = frappe.qb.DocType("Employee Group Table")
	employee = frappe.qb.DocType("Employee")
	return set(
		frappe.qb.from_(member)
		.join(employee)
		.on(member.employee == employee.name)
		.select(employee.user_id)
		.where(member.parent.isin([group.employee_group for group in available_employee_groups]))
		.where(employee.status == "Active")
		.where(employee.user_id.isnotnull() & (employee.user_id != ""))
		.run(pluck=True)
	)


def strip_number(number):
	if not number:
		return
	# strip + and 0 from the start of the number for proper number comparisions
	# eg. +7888383332 should match with 7888383332
	# eg. 07888383332 should match with 7888383332
	number = number.lstrip("+")
	number = number.lstrip("0")
	return number
