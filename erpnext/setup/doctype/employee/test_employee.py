# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe
import frappe.utils
from frappe.query_builder import Criterion

import erpnext
from erpnext.accounts.utils import build_qb_match_conditions
from erpnext.setup.doctype.employee.employee import InactiveEmployeeStatusError

test_records = frappe.get_test_records("Employee")


class TestEmployee(unittest.TestCase):
	def test_employee_status_left(self):
		employee1 = make_employee("test_employee_1@company.com")
		employee2 = make_employee("test_employee_2@company.com")
		employee1_doc = frappe.get_doc("Employee", employee1)
		employee2_doc = frappe.get_doc("Employee", employee2)
		employee2_doc.reload()
		employee2_doc.reports_to = employee1_doc.name
		employee2_doc.save()
		employee1_doc.reload()
		employee1_doc.status = "Left"
		self.assertRaises(InactiveEmployeeStatusError, employee1_doc.save)

	def test_user_has_employee(self):
		employee = make_employee("test_emp_user_creation@company.com")
		employee_doc = frappe.get_doc("Employee", employee)
		user = employee_doc.user_id
		self.assertTrue("Employee" in frappe.get_roles(user))
		employee_doc.user_id = ""
		employee_doc.save()
		self.assertTrue("Employee" not in frappe.get_roles(user))

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

	def test_hr_roles_link_any_user_except_admins(self):
		from frappe.permissions import add_permission, reset_perms

		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		user_admin_role = "_Test User Administrator"
		if not frappe.db.exists("Role", user_admin_role):
			frappe.get_doc({"doctype": "Role", "role_name": user_admin_role}).insert()
		if not frappe.db.exists("Custom DocPerm", {"parent": "User"}):
			self.addCleanup(reset_perms, "User")
		add_permission("User", user_admin_role, ptype="write")
		self.addCleanup(frappe.clear_cache, doctype="User")

		admins = [
			make_fenced_user("employee-manager@example.com", ["System Manager"]),
			make_fenced_user("employee-user-admin@example.com", [user_admin_role]),
		]
		sales_user = make_fenced_user("employee-sales@example.com", ["Sales User"])
		for hr_role in ("HR User", "HR Manager"):
			frappe.db.delete("Employee", {"user_id": ("in", [*admins, sales_user])})
			hr_user = make_fenced_user(f"employee-{frappe.scrub(hr_role)}@example.com", [hr_role])
			with as_user(hr_user):
				for admin in admins:
					self.assertRaises(frappe.PermissionError, new_employee(admin).insert)
				new_employee(sales_user).insert()

	def test_hr_user_toggles_user_permission_only_for_non_admin_users(self):
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
			manager_employee = frappe.get_doc("Employee", employees[manager])
			manager_employee.create_user_permission = 0
			self.assertRaises(frappe.PermissionError, manager_employee.save)

			staff_employee = frappe.get_doc("Employee", employees[staff])
			staff_employee.create_user_permission = 0
			staff_employee.save()

		for user, expected in ((manager, True), (staff, False)):
			has_permission = frappe.db.exists(
				"User Permission", {"allow": "Employee", "for_value": employees[user], "user": user}
			)
			self.assertEqual(bool(has_permission), expected)

	def test_employee_user_permission(self):
		employee1 = make_employee("employee_1_test@company.com", create_user_permission=1)
		employee2 = make_employee("employee_2_test@company.com", create_user_permission=1)
		make_employee("employee_3_test@company.com", create_user_permission=1)

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
			.orderby(Employee.Name)
		).run(pluck=Employee.name)
		employee_list = frappe.db.get_list("Employee", pluck="name", order_by="name")

		self.assertEqual(qb_employee_list, employee_list)
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()


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
