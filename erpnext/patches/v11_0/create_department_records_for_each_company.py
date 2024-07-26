import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree


def execute():
	frappe.local.lang = frappe.db.get_default("lang") or "en"

	for doctype in ["department", "leave_period", "staffing_plan", "job_opening"]:
		frappe.reload_doc("hr", "doctype", doctype)
	frappe.reload_doc("Payroll", "doctype", "payroll_entry")

	companies = frappe.db.get_all("Company", fields=["name", "abbr"])
	departments = frappe.db.get_all("Department")
	comp_dict = {}

	# create a blank list for each company
	for company in companies:
		comp_dict[company.name] = {}

	for department in departments:
		# skip root node
		if _(department.name) == _("All Departments"):
			continue

		# for each company, create a copy of the doc
		department_doc = frappe.get_doc("Department", department)
		for company in companies:
			copy_doc = frappe.copy_doc(department_doc)
			copy_doc.update({"company": company.name})
			try:
				copy_doc.insert()
			except frappe.DuplicateEntryError:
				pass
			# append list of new department for each company
			comp_dict[company.name][department.name] = copy_doc.name

	rebuild_tree("Department")
	doctypes = ["Asset", "Employee", "Payroll Entry", "Staffing Plan", "Job Opening"]

	for d in doctypes:
		update_records(d, comp_dict)

	update_instructors(comp_dict)

	frappe.local.lang = "en"


def update_records(doctype, comp_dict):
	when_then = []
	for company in comp_dict:
		records = comp_dict[company]

		for department in records:
			when_then.append(
				f"""
				WHEN company = "{company}" and department = "{department}"
				THEN "{records[department]}"
			"""
			)

	if not when_then:
		return

	frappe.db.sql(
		"""
		update
			`tab{}`
		set
			department = CASE {} END
	""".format(doctype, " ".join(when_then))
	)


def update_instructors(comp_dict):
	when_then = []
	emp_details = frappe.get_all("Employee", fields=["name", "company"])

	for employee in emp_details:
		records = comp_dict[employee.company] if employee.company else []

		for department in records:
			when_then.append(
				f"""
				WHEN employee = "{employee.name}" and department = "{department}"
				THEN "{records[department]}"
			"""
			)

	if not when_then:
		return

	frappe.db.sql(
		"""
		update
			`tabInstructor`
		set
			department = CASE %s END
	"""
		% (" ".join(when_then))
	)
