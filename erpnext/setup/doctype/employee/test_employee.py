# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import frappe.utils
from frappe.query_builder import Criterion

import erpnext
from erpnext.setup.doctype.employee.employee import InactiveEmployeeStatusError
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.query import get_match_conditions_qb


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

	def test_hr_user_cannot_unlink_or_reenable_admin_users(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		hr_user = make_fenced_user("employee-hr@example.com", ["HR User"])
		manager = make_fenced_user("employee-linked-manager@example.com", ["System Manager", "Employee"])
		frappe.db.set_value("User", manager, "enabled", 1)
		frappe.db.delete("Employee", {"user_id": manager})
		employee = make_employee(manager, company="_Test Company")

		with as_user(hr_user):
			linked = frappe.get_doc("Employee", employee)
			linked.user_id = ""
			self.assertRaises(frappe.PermissionError, linked.save)
		self.assertEqual(frappe.db.get_value("Employee", employee, "user_id"), manager)
		self.assertIn("Employee", frappe.get_roles(manager))

		frappe.db.set_value("User", manager, "enabled", 0)
		with as_user(hr_user):
			linked = frappe.get_doc("Employee", employee)
			linked.cell_number = "9999999999"
			linked.save()
		self.assertEqual(frappe.db.get_value("User", manager, "enabled"), 0)

	def test_hr_roles_cannot_link_users_without_user_write_access(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		sales_user = make_fenced_user("employee-sales@example.com", ["Sales User"])
		for hr_role in ("HR User", "HR Manager"):
			frappe.db.delete("Employee", {"user_id": sales_user})
			hr_user = make_fenced_user(f"employee-{frappe.scrub(hr_role)}@example.com", [hr_role])
			with as_user(hr_user):
				self.assertRaises(frappe.PermissionError, new_employee(sales_user).insert)

	def test_hr_user_cannot_toggle_user_permission_without_user_write_access(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		hr_user = make_fenced_user("employee-hr@example.com", ["HR User"])
		manager = make_fenced_user("employee-manager@example.com", ["System Manager"])
		staff = make_fenced_user("employee-staff@example.com", ["Employee"])
		employees = {}
		for user in (manager, staff):
			frappe.db.set_value("User", user, "enabled", 1)
			frappe.db.delete("Employee", {"user_id": user})
			employees[user] = make_employee(user, company="_Test Company", create_user_permission=1)

		with as_user(hr_user):
			for user in (manager, staff):
				employee = frappe.get_doc("Employee", employees[user])
				employee.create_user_permission = 0
				self.assertRaises(frappe.PermissionError, employee.save)

		for user in (manager, staff):
			has_permission = frappe.db.exists(
				"User Permission", {"allow": "Employee", "for_value": employees[user], "user": user}
			)
			self.assertTrue(has_permission)

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
			.where(Criterion.all(get_match_conditions_qb("Employee")))
			.orderby(Employee.name)
		).run(pluck=Employee.name)
		employee_list = frappe.db.get_list("Employee", pluck="name", order_by="name")

		self.assertEqual(qb_employee_list, employee_list)
		frappe.set_user("Administrator")

	def test_employee_role_can_only_read_linked_employee(self):
		from erpnext.tests.permission_test_utils import as_user

		user = "employee-read-own@example.com"
		employee = make_employee(user, company="_Test Company", create_user_permission=0)
		other_employee = make_employee(
			"employee-read-other@example.com", company="_Test Company", create_user_permission=0
		)
		frappe.get_doc("User", user).add_roles("Accounts User")

		with as_user(user):
			self.assertTrue(frappe.has_permission("Employee", "read", employee))
			self.assertFalse(frappe.has_permission("Employee", "read", other_employee))
			self.assertNotIn(other_employee, frappe.get_list("Employee", pluck="name"))

	def test_changing_user_removes_old_user_access(self):
		from erpnext.tests.permission_test_utils import make_fenced_user

		old_user = "employee-old-user@example.com"
		new_user = make_fenced_user("employee-new-user@example.com", ["Employee"])
		employee = make_employee(old_user, company="_Test Company", create_user_permission=1)
		company_permission = frappe.db.get_value(
			"User Permission",
			{
				"allow": "Company",
				"for_value": "_Test Company",
				"user": old_user,
				"apply_to_all_doctypes": 1,
			},
			["apply_to_all_doctypes", "applicable_for"],
			as_dict=True,
		)
		self.assertTrue(company_permission.apply_to_all_doctypes)
		self.assertFalse(company_permission.applicable_for)

		employee_doc = frappe.get_doc("Employee", employee)
		employee_doc.user_id = new_user
		employee_doc.save()

		for allow, for_value in (("Employee", employee), ("Company", "_Test Company")):
			self.assertFalse(
				frappe.db.exists(
					"User Permission", {"allow": allow, "for_value": for_value, "user": old_user}
				)
			)
		self.assertNotIn("Employee", frappe.get_roles(old_user))

	def test_changing_company_replaces_company_user_permission(self):
		user = "employee-company-change@example.com"
		employee = make_employee(user, company="_Test Company", create_user_permission=1)

		employee_doc = frappe.get_doc("Employee", employee)
		employee_doc.company = "_Test Company 1"
		employee_doc.save()

		self.assertFalse(
			frappe.db.exists(
				"User Permission", {"allow": "Company", "for_value": "_Test Company", "user": user}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"User Permission", {"allow": "Company", "for_value": "_Test Company 1", "user": user}
			)
		)

	def test_unlinking_left_employee_preserves_rehire_role(self):
		user = "employee-rehire@example.com"
		former_employee = make_employee(user, company="_Test Company")

		former_employee_doc = frappe.get_doc("Employee", former_employee)
		former_employee_doc.status = "Left"
		former_employee_doc.relieving_date = "2024-01-01"
		former_employee_doc.save()
		new_employee(user).insert()

		former_employee_doc.reload()
		former_employee_doc.user_id = ""
		former_employee_doc.save()

		self.assertIn("Employee", frappe.get_roles(user))

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


def new_employee(user_id: str):
	return frappe.get_doc(
		doctype="Employee",
		first_name=user_id,
		company="_Test Company",
		user_id=user_id,
		date_of_birth="1990-05-08",
		date_of_joining="2013-01-01",
		gender="Female",
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
