import frappe
from frappe import _
from frappe.utils import getdate

@frappe.whitelist()
def create_employee_records():
	company = create_company()
	create_missing_designation()

	emp1 = create_employee('Test Employee 1', 'CEO')
	emp2 = create_employee('Test Employee 2', 'CTO')
	emp3 = create_employee('Test Employee 3', 'Head of Marketing and Sales', emp1)
	emp4 = create_employee('Test Employee 4', 'Project Manager', emp2)
	emp5 = create_employee('Test Employee 5', 'Engineer', emp2)
	emp6 = create_employee('Test Employee 6', 'Analyst', emp3)
	emp7 = create_employee('Test Employee 7', 'Software Developer', emp4)

	employees = [emp1, emp2, emp3, emp4, emp5, emp6, emp7]
	return employees

def create_company():
	company = frappe.db.exists('Company', 'Test Org Chart')
	if not company:
		company = frappe.get_doc({
			'doctype': 'Company',
			'company_name': 'Test Org Chart',
			'country': 'India',
			'default_currency': 'INR'
		}).insert().name

	return company

def create_employee(first_name, designation, reports_to=None):
	employee = frappe.db.exists('Employee', {'first_name': first_name, 'designation': designation})
	if not employee:
		employee = frappe.get_doc({
			'doctype': 'Employee',
			'first_name': first_name,
			'company': 'Test Org Chart',
			'gender': 'Female',
			'date_of_birth': getdate('08-12-1998'),
			'date_of_joining': getdate('01-01-2021'),
			'designation': designation,
			'reports_to': reports_to
		}).insert().name

	return employee

def create_missing_designation():
	if not frappe.db.exists('Designation', 'CTO'):
		frappe.get_doc({
			'doctype': 'Designation',
			'designation_name': 'CTO'
		}).insert()