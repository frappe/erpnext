# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestSalesPartner(IntegrationTestCase):
	def make_partner(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Sales Partner",
				"partner_name": "Test Partner " + frappe.generate_hash(length=10),
				"territory": "All Territories",
				"commission_rate": 5,
				**values,
			}
		).insert()

	def test_published_partner_address_context(self):
		partner = self.make_partner(show_in_website=1)
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": partner.name,
				"address_type": "Office",
				"address_line1": "12 Main Road",
				"address_line2": "Floor 2",
				"city": "Mumbai",
				"country": "India",
				"phone": "111,222",
				"links": [{"link_doctype": "Sales Partner", "link_name": partner.name}],
			}
		).insert()

		context = partner.get_context(frappe._dict())

		self.assertEqual(context.addresses[0]["partner_address"], "12 Main Road\nFloor 2\nMumbai\nIndia")
		self.assertEqual(context.addresses[0]["phone"], "111\n222")

	def test_partner_address_rendering_escapes_content(self):
		template = frappe.get_jenv().get_template("templates/generators/sales_partner.html")
		context = template.new_context(
			{
				"addresses": [
					{
						"partner_address": "<script>alert(1)</script>\nFloor 2",
						"phone": "111\n<img src=x onerror=alert(1)>",
					}
				],
			}
		)
		html = "".join(template.blocks["page_content"](context))

		self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;<br>Floor 2", html)
		self.assertIn("111<br>&lt;img src=x onerror=alert(1)&gt;", html)
		self.assertNotIn("<script>", html)
		self.assertNotIn("<img src=x", html)
