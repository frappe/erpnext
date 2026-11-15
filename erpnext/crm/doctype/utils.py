import frappe

# Phone numbers are compared on their last 10 digits, so that country and trunk prefixes are ignored.
PHONE_NUMBER_MATCH_LENGTH = 10
MINIMUM_PHONE_NUMBER_LENGTH = 7


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

	medium = frappe.db.get_value(
		"Communication Medium", communication_medium, ["disabled", "catch_all"], as_dict=True
	)
	if medium and medium.disabled:
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

	available_employee_groups = tuple([emp.employee_group for emp in available_employee_groups])
	if not available_employee_groups and medium and medium.catch_all:
		available_employee_groups = (medium.catch_all,)
	if not available_employee_groups:
		return set()

	member = frappe.qb.DocType("Employee Group Table")
	employee = frappe.qb.DocType("Employee")
	return set(
		frappe.qb.from_(member)
		.join(employee)
		.on(member.employee == employee.name)
		.select(employee.user_id)
		.where(member.parent.isin(available_employee_groups))
		.where(employee.status == "Active")
		.where(employee.user_id.isnotnull() & (employee.user_id != ""))
		.run(pluck=True)
	)


def strip_number(number: str | None) -> str | None:
	"""Return only the digits of the number, without leading zeros.

	eg. "+91 78883-83332" becomes "917888383332" and "07888383332" becomes "7888383332"
	"""
	if not number:
		return
	return "".join(character for character in number if character.isdigit()).lstrip("0")


def get_phone_number_key(number: str | None) -> str | None:
	"""Return the last digits used to compare phone numbers, or None if the number is too short to match."""
	digits = strip_number(number)
	if not digits or len(digits) < MINIMUM_PHONE_NUMBER_LENGTH:
		return None
	return digits[-PHONE_NUMBER_MATCH_LENGTH:]


def get_phone_number_like_pattern(key: str) -> str:
	"""Return a broad LIKE pattern for stored numbers containing the key's last digits, in any format."""
	return "%" + "%".join(key[-MINIMUM_PHONE_NUMBER_LENGTH:]) + "%"


def get_contacts_with_phone_number(number: str | None) -> list[str]:
	"""Return all contacts with a phone number matching the given number."""
	if not (key := get_phone_number_key(number)):
		return []

	phones = frappe.get_all(
		"Contact Phone",
		filters={"parenttype": "Contact", "phone": ["like", get_phone_number_like_pattern(key)]},
		fields=["parent", "phone"],
	)
	return list(dict.fromkeys(phone.parent for phone in phones if get_phone_number_key(phone.phone) == key))
