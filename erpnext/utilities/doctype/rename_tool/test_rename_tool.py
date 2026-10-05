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
			patch.object(frappe.db, "rollback"),
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


def attach_csv(content: str) -> str:
	return save_file("rename.csv", content.encode(), "Rename Tool", "Rename Tool", is_private=1).file_url


def run_job_inline(method, **kwargs):
	if callable(method):
		kwargs.pop("queue", None)
		return method(**kwargs)
