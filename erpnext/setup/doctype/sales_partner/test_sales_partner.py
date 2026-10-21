# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

test_records = frappe.get_test_records("Sales Partner")

test_ignore = ["Item Group"]


class TestSalesPartner(FrappeTestCase):
	def test_partner_address_rendering_escapes_content(self):
		template = frappe.get_jenv().get_template("templates/generators/sales_partner.html")
		context = template.new_context(
			{
				"partner_address": "<script>alert(1)</script>\nFloor 2",
				"phone": "111\n<img src=x onerror=alert(1)>",
			}
		)
		html = "".join(template.blocks["page_content"](context))

		self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;<br>Floor 2", html)
		self.assertIn("111<br>&lt;img src=x onerror=alert(1)&gt;", html)
		self.assertNotIn("<script>", html)
		self.assertNotIn("<img src=x", html)
