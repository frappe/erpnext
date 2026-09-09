# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBoot(ERPNextTestSuite):
	def test_boot_session_drops_disabled_price_list_default(self):
		from erpnext.startup.boot import boot_session

		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": frappe.generate_hash(length=10),
				"currency": "INR",
				"selling": 1,
				"enabled": 0,
			}
		).insert(ignore_permissions=True)

		bootinfo = frappe._dict(
			sysdefaults=frappe._dict(selling_price_list=price_list.name),
			page_info=frappe._dict(),
			docs=[],
		)
		boot_session(bootinfo)

		self.assertIsNone(bootinfo.sysdefaults.get("selling_price_list"))
