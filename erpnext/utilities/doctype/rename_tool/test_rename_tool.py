# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils.file_manager import save_file

from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.doctype.rename_tool.rename_tool import upload


class TestRenameTool(ERPNextTestSuite):
	def setUp(self):
		for patched in (
			patch("frappe.enqueue", side_effect=run_job_inline),
			patch.object(frappe.db, "commit"),
		):
			patched.start()
			self.addCleanup(patched.stop)

	def test_each_run_uses_its_own_file(self):
		first, second = make_customer("_Test Rename Tool A"), make_customer("_Test Rename Tool B")

		upload("Customer", attach_csv(f"{first},{first} Renamed\n"))
		self.assertTrue(frappe.db.exists("Customer", f"{first} Renamed"))
		self.assertFalse(frappe.db.exists("File", {"attached_to_doctype": "Rename Tool"}))

		upload("Customer", attach_csv(f"{second},{second} Renamed\n"))
		self.assertTrue(frappe.db.exists("Customer", f"{second} Renamed"))

	def test_upload_requires_rename_tool_access_and_a_renameable_doctype(self):
		customer = make_customer("_Test Rename Tool C")
		file_url = attach_csv(f"{customer},{customer} Renamed\n")

		self.assertRaises(frappe.ValidationError, upload, "Role", file_url)

		frappe.get_doc("User", "test1@example.com").add_roles("Sales Manager")
		frappe.set_user("test1@example.com")
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertRaises(frappe.PermissionError, upload, "Customer", file_url)
		self.assertFalse(frappe.db.exists("Customer", f"{customer} Renamed"))

	def test_failed_rows_are_reported_to_the_user(self):
		customer, existing = make_customer("_Test Rename Tool D"), make_customer("_Test Rename Tool E")
		csv = f"{customer},{existing}\n_Test Rename Tool Missing,_Test Rename Tool X\n"

		with patch.object(frappe.db, "rollback"):
			upload("Customer", attach_csv(csv))

		notification = frappe.get_last_doc("Notification Log", {"for_user": "Administrator"})
		self.assertIn("2 of 2", notification.subject)
		self.assertIn(existing, notification.email_content)
		self.assertIn("_Test Rename Tool Missing", notification.email_content)


def attach_csv(content: str) -> str:
	return save_file("rename.csv", content.encode(), "Rename Tool", "Rename Tool", is_private=1).file_url


def run_job_inline(method, **kwargs):
	if callable(method):
		kwargs.pop("queue", None)
		return method(**kwargs)
