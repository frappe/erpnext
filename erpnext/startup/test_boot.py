# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBoot(ERPNextTestSuite):
	def test_boot_session_populates_companies_and_party_types(self):
		# boot_session reads Customer count, Company list and Party Type account types via ORM/qb
		# (formerly raw SQL with ifnull, which is invalid on Postgres). Exercises that on both engines.
		from erpnext.startup.boot import boot_session

		bootinfo = frappe._dict(sysdefaults=frappe._dict(), page_info=frappe._dict(), docs=[])
		boot_session(bootinfo)

		self.assertIsInstance(bootinfo.customer_count, int)
		self.assertIn("party_account_types", bootinfo)

		company_docs = [d for d in bootinfo.docs if d.get("doctype") == ":Company"]
		self.assertTrue(any(d.get("name") == "_Test Company" for d in company_docs))
