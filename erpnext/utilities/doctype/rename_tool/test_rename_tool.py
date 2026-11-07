# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.utilities.doctype.rename_tool.rename_tool import upload


class TestRenameTool(FrappeTestCase):
	def setUp(self):
		for patched in (
			patch("frappe.enqueue", side_effect=run_job_inline),
			patch.object(frappe.db, "commit"),
		):
			patched.start()
			self.addCleanup(patched.stop)

	def tearDown(self):
		frappe.db.rollback()

	def test_each_run_uses_its_own_file(self):
		first, second = make_customer("_Test Rename Tool A"), make_customer("_Test Rename Tool B")

		upload("Customer", attach_csv(f"{first},{first} Renamed\n"))
		self.assertTrue(frappe.db.exists("Customer", f"{first} Renamed"))
		self.assertFalse(frappe.db.exists("File", {"attached_to_doctype": "Rename Tool"}))

		upload("Customer", attach_csv(f"{second},{second} Renamed\n"))
		self.assertTrue(frappe.db.exists("Customer", f"{second} Renamed"))

	def test_file_saved_in_the_attach_field_is_removed(self):
		customer = make_customer("_Test Rename Tool F")
		file_url = attach_csv(f"{customer},{customer} Renamed\n")
		frappe.db.set_single_value("Rename Tool", "file_to_rename", file_url)

		upload("Customer", file_url)
		self.assertTrue(frappe.db.exists("Customer", f"{customer} Renamed"))
		self.assertFalse(frappe.db.exists("File", {"file_url": file_url}))
		self.assertFalse(frappe.db.get_single_value("Rename Tool", "file_to_rename"))


def attach_csv(content: str) -> str:
	return save_file("rename.csv", content.encode(), "Rename Tool", "Rename Tool", is_private=1).file_url


def run_job_inline(method, **kwargs):
	if callable(method):
		kwargs.pop("queue", None)
		kwargs.pop("enqueue_after_commit", None)
		return method(**kwargs)
