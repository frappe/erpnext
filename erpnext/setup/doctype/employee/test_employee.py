# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import frappe.utils
from frappe.query_builder import Criterion

import erpnext
from erpnext.accounts.utils import build_qb_match_conditions
from erpnext.setup.doctype.employee.employee import InactiveEmployeeStatusError
from erpnext.tests.utils import ERPNextTestSuite


class TestEmployee(ERPNextTestSuite):
	def test_employee_status_left(self):
		employee1 = make_employee("test_employee_1@company.com", company="_Test Company")
		employee2 = make_employee("test_employee_2@company.com", company="_Test Company")
		employee1_doc = frappe.get_doc("Employee", employee1)
		employee2_doc = frappe.get_doc("Employee", employee2)
		employee2_doc.reload()
		employee2_doc.reports_to = employee1_doc.name
		employee2_doc.save()
		employee1_doc.reload()
		employee1_doc.status = "Left"
		self.assertRaises(InactiveEmployeeStatusError, employee1_doc.save)

	def test_user_has_employee(self):
		employee = make_employee("test_emp_user_creation@company.com", company="_Test Company")
		employee_doc = frappe.get_doc("Employee", employee)
		user = employee_doc.user_id
		self.assertIn("Employee", frappe.get_roles(user))
		employee_doc.user_id = ""
		employee_doc.save()
		self.assertNotIn("Employee", frappe.get_roles(user))

	def test_employee_user_permission(self):
		employee1 = make_employee(
			"employee_1_test@company.com", create_user_permission=1, company="_Test Company"
		)
		employee2 = make_employee(
			"employee_2_test@company.com", create_user_permission=1, company="_Test Company"
		)
		make_employee("employee_3_test@company.com", create_user_permission=1, company="_Test Company")

		employee1_doc = frappe.get_doc("Employee", employee1)
		employee2_doc = frappe.get_doc("Employee", employee2)

		employee2_doc.reload()
		employee2_doc.reports_to = employee1_doc.name
		employee2_doc.save()

		frappe.set_user(employee1_doc.user_id)

		Employee = frappe.qb.DocType("Employee")
		qb_employee_list = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where(Criterion.all(build_qb_match_conditions("Employee")))
			.orderby(Employee.name)
		).run(pluck=Employee.name)
		employee_list = frappe.db.get_list("Employee", pluck="name", order_by="name")

		self.assertEqual(qb_employee_list, employee_list)
		frappe.set_user("Administrator")

	def test_disabled_department_cannot_be_assigned(self):
		department = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": "Employee Disabled Department",
				"company": "_Test Company",
			}
		).insert()
		employee = frappe.get_doc(
			"Employee",
			make_employee(
				"test_disabled_department@company.com",
				company="_Test Company",
				department=department.name,
			),
		)
		other_doc = frappe.get_doc(
			"Employee",
			make_employee(
				"test_other_department@company.com", company="_Test Company", department=department.name
			),
		)
		department.disabled = 1
		department.save()

		# Existing assignments remain valid until the department link changes.
		employee.save()
		other_doc.department = None
		other_doc.save()
		other_doc.department = department.name
		with self.assertRaisesRegex(frappe.ValidationError, "disabled Department"):
			other_doc.save()

		with self.assertRaisesRegex(frappe.ValidationError, "disabled Department"):
			frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": "Disabled Department Test",
					"company": "_Test Company",
					"department": department.name,
					"gender": "Female",
					"date_of_birth": "1990-05-08",
					"date_of_joining": "2013-01-01",
				}
			).insert()

	def test_salary_currency_set_from_company(self):
		employee = make_employee("test_emp_salary_currency@company.com", company="_Test Company 1")
		self.assertEqual(frappe.db.get_value("Employee", employee, "salary_currency"), "USD")

	def test_salary_currency_not_overridden_if_set(self):
		employee = make_employee(
			"test_emp_salary_currency_set@company.com",
			company="_Test Company 1",
			salary_currency="EUR",
		)
		self.assertEqual(frappe.db.get_value("Employee", employee, "salary_currency"), "EUR")

	def test_create_user_automatically(self):
		def get_new_employee(email: str, create_user_permission: int):
			return frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": "Test Auto User 1",
					"company": "_Test Company",
					"date_of_birth": "2000-05-08",
					"date_of_joining": "2013-01-01",
					"gender": "Female",
					"personal_email": email,
					"status": "Active",
					"create_user_automatically": 1,
					"create_user_permission": create_user_permission,
				}
			).insert()

		employee1 = get_new_employee("test_auto_user1@example.com", True)
		user = frappe.db.get_value("User", "test_auto_user1@example.com")
		self.assertTrue(user)
		self.assertEqual(employee1.user_id, user)

		# Verify user permissions are created
		self.assertTrue(
			frappe.db.exists(
				"User Permission", {"allow": "Employee", "for_value": employee1.name, "user": user}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"User Permission", {"allow": "Company", "for_value": employee1.company, "user": user}
			)
		)

		# Test disabled create_user_permission
		employee2 = get_new_employee("test_auto_user2@example.com", False)
		user2 = frappe.db.get_value("User", "test_auto_user2@example.com")
		self.assertTrue(user2)
		self.assertEqual(employee2.user_id, user2)

		# Verify user permissions are not created
		self.assertFalse(
			frappe.db.exists(
				"User Permission", {"allow": "Employee", "for_value": employee2.name, "user": user2}
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"User Permission", {"allow": "Company", "for_value": employee2.company, "user": user2}
			)
		)


def make_employee(user, company=None, **kwargs):
	if not frappe.db.get_value("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": user,
				"new_password": "password",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": "Employee"}],
			}
		).insert()

	if not frappe.db.get_value("Employee", {"user_id": user}):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "EMP-",
				"first_name": user,
				"company": company or erpnext.get_default_company(),
				"user_id": user,
				"date_of_birth": "1990-05-08",
				"date_of_joining": "2013-01-01",
				"department": frappe.get_all("Department", fields="name")[0].name,
				"gender": "Female",
				"company_email": user,
				"prefered_contact_email": "Company Email",
				"prefered_email": user,
				"status": "Active",
				"employment_type": "Intern",
			}
		)
		if kwargs:
			employee.update(kwargs)
		employee.insert()
		return employee.name
	else:
		employee = frappe.get_doc("Employee", {"employee_name": user})
		employee.update(kwargs)
		employee.status = "Active"
		employee.save()
		return employee.name
