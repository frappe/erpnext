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

	def test_commission_rate_available_with_select_permission(self):
		from erpnext.setup.doctype.sales_partner.sales_partner import get_commission_rate
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		partner = self.make_partner(commission_rate=8)
		for role in ("Accounts User", "Delivery User"):
			with self.subTest(role=role):
				user = make_fenced_user(
					"partner-commission-" + frappe.generate_hash(length=10) + "@example.com", [role]
				)
				with as_user(user):
					self.assertFalse(frappe.has_permission("Sales Partner", "read", doc=partner))
					self.assertTrue(frappe.has_permission("Sales Partner", "select", doc=partner))
					self.assertEqual(get_commission_rate(partner.name), 8)

		with as_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				get_commission_rate(partner.name)

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

	def test_commission_follows_partner_changes(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		partners = [self.make_partner(commission_rate=rate) for rate in (5, 8, 0)]
		frappe.db.set_value("Item", "_Test Item", "grant_commission", 1)
		for factory in (make_sales_order, create_delivery_note, create_sales_invoice):
			with self.subTest(factory=factory.__name__):
				doc = factory(qty=10, rate=100, do_not_save=True)
				doc.sales_partner = partners[0].name
				self.assertIsNone(doc.commission_rate)
				doc.save()
				self.assertEqual(doc.commission_rate, 5)
				self.assertEqual(doc.total_commission, 50)

				doc.commission_rate = 7
				doc.save()
				self.assertEqual(doc.total_commission, 70)

				doc.commission_rate = 6
				doc.save()
				self.assertEqual(doc.total_commission, 60)

				doc.sales_partner = partners[1].name
				doc.save()
				self.assertEqual(doc.commission_rate, 8)
				self.assertEqual(doc.total_commission, 80)

				doc.sales_partner = partners[2].name
				doc.save()
				self.assertEqual(doc.commission_rate, 0)
				self.assertEqual(doc.total_commission, 0)

				doc.sales_partner = None
				doc.commission_rate = 10
				doc.append("sales_team", {"sales_person": "_Test Sales Person", "allocated_percentage": 100})
				doc.save()
				self.assertEqual(doc.commission_rate, 0)
				self.assertEqual(doc.total_commission, 0)
				self.assertEqual(doc.amount_eligible_for_commission, 1000)
				self.assertEqual(doc.sales_team[0].allocated_amount, 1000)

	def test_partner_change_preserves_explicit_commission_rate(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		partners = [self.make_partner(commission_rate=rate) for rate in (5, 8)]
		frappe.db.set_value("Item", "_Test Item", "grant_commission", 1)
		for factory in (make_sales_order, create_delivery_note, create_sales_invoice):
			for rate in (6, 0):
				with self.subTest(factory=factory.__name__, rate=rate):
					doc = factory(qty=10, rate=100, do_not_save=True)
					doc.sales_partner = partners[0].name
					doc.commission_rate = 7
					doc.save()

					doc.sales_partner = partners[1].name
					doc.commission_rate = rate
					doc.save()
					doc.reload()
					self.assertEqual(doc.commission_rate, rate)
					self.assertEqual(doc.total_commission, 1000 * rate / 100)

	def test_commission_without_partner(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		frappe.db.set_value("Item", "_Test Item", "grant_commission", 1)
		for factory in (make_sales_order, create_delivery_note, create_sales_invoice):
			with self.subTest(factory=factory.__name__):
				doc = factory(qty=10, rate=100, do_not_save=True)
				doc.sales_partner = None
				doc.commission_rate = 10
				doc.save()
				self.assertEqual(doc.commission_rate, 0)
				self.assertEqual(doc.total_commission, 0)
				self.assertEqual(doc.amount_eligible_for_commission, 1000)

	def test_selected_partner_defaults_before_customer_commission(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		customer_partner = self.make_partner(commission_rate=5)
		selected_partner = self.make_partner(commission_rate=8)
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.default_sales_partner = customer_partner.name
		customer.default_commission_rate = 5
		customer.save()

		for factory in (make_sales_order, create_delivery_note, create_sales_invoice):
			with self.subTest(factory=factory.__name__):
				doc = factory(qty=10, rate=100, do_not_save=True)
				doc.sales_partner = selected_partner.name
				self.assertIsNone(doc.commission_rate)
				doc.save()
				self.assertEqual(doc.commission_rate, 8)
				self.assertEqual(doc.total_commission, 80)

				default_doc = factory(qty=10, rate=100, do_not_save=True)
				default_doc.save()
				self.assertEqual(default_doc.sales_partner, customer_partner.name)
				self.assertEqual(default_doc.commission_rate, 5)
				self.assertEqual(default_doc.total_commission, 50)

	def test_invalid_targets_are_rejected(self):
		partner = self.make_partner()
		for qty, amount, message in (
			(0, 0, "Row #1: Either Target Qty or Target Amount is mandatory"),
			(-1, 10, "Row 1: Target Qty and Target Amount cannot be negative"),
			(1, -10, "Row 1: Target Qty and Target Amount cannot be negative"),
		):
			with self.subTest(qty=qty, amount=amount):
				partner.set("targets", [{"target_qty": qty, "target_amount": amount}])
				with self.assertRaisesRegex(frappe.ValidationError, message):
					partner.validate()

	def test_quantity_or_amount_targets_are_allowed(self):
		partner = self.make_partner()
		for qty, amount in ((10, 0), (0, 10), (10, 10)):
			with self.subTest(qty=qty, amount=amount):
				partner.set("targets", [{"target_qty": qty, "target_amount": amount}])
				partner.validate()
