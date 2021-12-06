import frappe
from frappe.utils.nestedset import get_root_of

def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	dts = ['Project', 'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']
	fieldnames = ['service_advisor', 'service_manager']

	exists = frappe.db.exists("Custom Field", {
		"fieldname": "service_advisor",
		"options": "Employee",
		"dt": ['in', dts]
	})

	if not exists:
		return

	employees = set()
	for dt in dts:
		for fieldname in fieldnames:
			service_persons = frappe.db.sql_list("select distinct {0} from `tab{1}`".format(fieldname, dt))
			for name in service_persons:
				if name:
					employees.add(name)

	employee_to_sales_person = {}
	root_sales_person = get_root_of("Sales Person")

	for employee in employees:
		employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		employee_to_sales_person[employee] = employee_name
		if not frappe.db.exists("Sales Person", employee_name):
			sales_person = frappe.new_doc("Sales Person")
			sales_person.parent_sales_person = root_sales_person
			sales_person.sales_person_name = employee_name
			sales_person.enabled = 1
			sales_person.insert()

	for dt in dts:
		for employee, sales_person in employee_to_sales_person.items():
			for fieldname in fieldnames:
				frappe.db.sql("""
					update `tab{0}`
					set {1} = %s
					where {1} = %s
				""".format(dt, fieldname), [sales_person, employee])

	# Delete Service Person Name fields
	frappe.db.sql("""
		delete
		from `tabCustom Field`
		where dt in %s and fieldname in ('service_advisor_name', 'service_manager_name')
	""", [dts])
