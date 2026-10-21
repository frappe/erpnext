# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesTeam(ERPNextTestSuite):
	def setUp(self):
		self.person = self.make_person(10)
		self.other_person = self.make_person(10)
		self.disabled_person = self.make_person(10)
		self.disabled_person.enabled = 0
		self.disabled_person.save()

	def test_sales_order_team_update_after_submit(self):
		self.check_team_update_after_submit("Sales Order")

	def test_delivery_note_team_update_after_submit(self):
		self.check_team_update_after_submit("Delivery Note")

	def test_sales_invoice_team_update_after_submit(self):
		self.check_team_update_after_submit("Sales Invoice")

	def test_pos_invoice_team_update_after_submit(self):
		self.check_team_update_after_submit("POS Invoice")

	def check_team_update_after_submit(self, doctype):
		doc = self.make_transaction(doctype)
		doc.submit()
		for team in (
			[
				{"sales_person": self.person.name, "allocated_percentage": 30},
				{"sales_person": self.other_person.name, "allocated_percentage": 30},
			],
			[{"sales_person": self.disabled_person.name, "allocated_percentage": 100}],
		):
			with self.subTest(team=team):
				doc.reload()
				doc.set("sales_team", team)
				with self.assertRaises(frappe.ValidationError):
					doc.save()

		doc.reload()
		doc.set(
			"sales_team",
			[
				{"sales_person": self.person.name, "allocated_percentage": 40},
				{"sales_person": self.other_person.name, "allocated_percentage": 60},
			],
		)
		doc.save()
		doc.reload()
		self.assertEqual([row.allocated_amount for row in doc.sales_team], [400, 600])
		self.assertEqual([row.incentives for row in doc.sales_team], [40, 60])

	def test_person_change_refreshes_zero_rate_and_incentives(self):
		doc = self.make_transaction()
		zero_person = self.make_person()
		doc.sales_team[0].sales_person = zero_person.name
		doc.sales_team[0].incentives = 999
		doc.save()
		doc.reload()
		self.assertEqual(doc.sales_team[0].commission_rate, 0)
		self.assertEqual(doc.sales_team[0].incentives, 0)

	def test_new_assignments_use_master_rate(self):
		doc = self.make_transaction()
		new_person = self.make_person(7)
		doc.sales_team[0].sales_person = new_person.name
		doc.sales_team[0].commission_rate = 99
		doc.save()
		self.assertEqual(doc.sales_team[0].commission_rate, 7)
		self.assertEqual(doc.sales_team[0].incentives, 70)
		doc.set(
			"sales_team",
			[{"sales_person": self.person.name, "allocated_percentage": 100, "commission_rate": 99}],
		)
		doc.save()
		self.assertEqual(doc.sales_team[0].commission_rate, 10)

	def test_unchanged_person_preserves_saved_rate(self):
		for rate in (0, 10):
			with self.subTest(rate=rate):
				self.person.commission_rate = rate
				self.person.save()
				doc = self.make_transaction()
				self.person.commission_rate = 20
				self.person.save()
				doc.sales_team[0].commission_rate = 99
				doc.save()
				doc.reload()
				self.assertEqual(doc.sales_team[0].commission_rate, rate)
				self.assertEqual(doc.sales_team[0].incentives, rate * 10)

	def test_invalid_master_rate_is_rejected(self):
		bad_person = self.make_person(500)
		doc = self.make_transaction()
		doc.sales_team[0].sales_person = bad_person.name
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_row_commission_rate_bounds(self):
		doc = self.make_transaction()
		for rate in (-1, 500):
			with self.subTest(rate=rate):
				doc.reload()
				doc.sales_team[0].commission_rate = rate
				with self.assertRaises(frappe.ValidationError):
					doc.save()

	def test_submitted_person_change_updates_rate(self):
		doc = self.make_transaction()
		doc.submit()
		doc.sales_team[0].sales_person = self.make_person(7).name
		doc.save()
		doc.reload()
		self.assertEqual(doc.sales_team[0].commission_rate, 7)
		self.assertEqual(doc.sales_team[0].incentives, 70)

	def test_returns_reverse_original_commission_rate(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		for doctype in ("Sales Invoice", "POS Invoice", "Delivery Note"):
			with self.subTest(doctype=doctype):
				self.person.commission_rate = 10
				self.person.save()
				doc = self.make_transaction(doctype)
				doc.submit()
				self.person.commission_rate = 20
				self.person.save()
				returned = make_return_doc(doctype, doc.name)
				returned.sales_team[0].commission_rate = 99
				returned.insert()
				returned.submit()
				returned.reload()
				self.assertEqual(returned.sales_team[0].commission_rate, 10)
				self.assertEqual(returned.sales_team[0].incentives, -doc.sales_team[0].incentives)

	def test_commission_preview_with_select_permission(self):
		from erpnext.setup.doctype.sales_person.sales_person import get_commission_rate

		for role in ("Accounts User", "Delivery User"):
			with self.subTest(role=role):
				user = frappe.get_doc(
					doctype="User",
					email=f"sales-team-{frappe.generate_hash(length=10)}@example.com",
					first_name="Sales Team",
					send_welcome_email=0,
					roles=[{"role": role}],
				).insert()
				try:
					frappe.set_user(user.name)
					self.assertFalse(frappe.has_permission("Sales Person", "read"))
					self.assertEqual(get_commission_rate(self.person.name), 10)
				finally:
					frappe.set_user("Administrator")

	def test_commission_preview_requires_select_permission(self):
		from erpnext.setup.doctype.sales_person.sales_person import get_commission_rate

		try:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.PermissionError):
				get_commission_rate(self.person.name)
		finally:
			frappe.set_user("Administrator")

	def test_mapped_sales_team_uses_current_master_rate(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		doc = self.make_transaction()
		doc.submit()
		self.person.commission_rate = 20
		self.person.save()
		invoice = make_sales_invoice(doc.name)
		invoice.insert()
		self.assertEqual(invoice.sales_team[0].commission_rate, 20)
		self.assertEqual(invoice.sales_team[0].incentives, 200)
		doc.reload()
		doc.save()
		self.assertEqual(doc.sales_team[0].commission_rate, 10)

	def test_disable_rejects_unfinished_sales_order(self):
		doc = self.make_transaction()
		doc.submit()
		self.person.enabled = 0
		with self.assertRaises(frappe.ValidationError):
			self.person.save()
		doc.update_status("Closed")
		self.person.reload()
		self.person.enabled = 0
		self.person.save()
		self.assertFalse(self.person.enabled)

	def test_disable_rejects_unbilled_delivery_note(self):
		doc = self.make_transaction("Delivery Note")
		doc.submit()
		self.person.enabled = 0
		with self.assertRaises(frappe.ValidationError):
			self.person.save()
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

		make_sales_invoice(doc.name).insert().submit()
		doc.reload()
		self.assertEqual(doc.per_billed, 100)
		self.person.reload()
		self.person.enabled = 0
		self.person.save()
		self.assertFalse(self.person.enabled)

	def test_disable_allows_draft_cancelled_and_completed_orders(self):
		self.make_transaction()
		cancelled = self.make_transaction()
		cancelled.submit()
		cancelled.cancel()
		completed = self.make_transaction()
		completed.submit()
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note, make_sales_invoice

		make_delivery_note(completed.name).insert().submit()
		make_sales_invoice(completed.name).insert().submit()
		completed.reload()
		self.assertEqual(completed.status, "Completed")
		self.person.enabled = 0
		self.person.save()
		self.assertFalse(self.person.enabled)

	def test_disable_allows_closed_delivery_and_unpaid_invoice(self):
		delivery = self.make_transaction("Delivery Note")
		delivery.submit()
		delivery.update_status("Closed")
		invoice = self.make_transaction("Sales Invoice")
		invoice.submit()
		self.assertGreater(invoice.outstanding_amount, 0)
		self.person.enabled = 0
		self.person.save()
		self.assertFalse(self.person.enabled)

	def make_transaction(self, doctype="Sales Order"):
		factory = {
			"Sales Order": make_sales_order,
			"Delivery Note": create_delivery_note,
			"Sales Invoice": create_sales_invoice,
			"POS Invoice": create_pos_invoice,
		}[doctype]
		doc = factory(item_code="_Test Non Stock Item", qty=1, rate=1000, do_not_save=True)
		if doctype == "POS Invoice":
			from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry

			frappe.db.set_single_value("POS Settings", "invoice_type", "POS Invoice")
			create_opening_entry(frappe.get_doc("POS Profile", doc.pos_profile), frappe.session.user)
			doc.set("payments", [{"mode_of_payment": "Cash", "amount": 1000}])
		doc.set("sales_team", [{"sales_person": self.person.name, "allocated_percentage": 100}])
		doc.insert()
		return doc

	def make_person(self, rate=0, is_group=0):
		return frappe.get_doc(
			doctype="Sales Person",
			sales_person_name=f"_Test Sales Team {frappe.generate_hash(length=10)}",
			commission_rate=rate,
			is_group=is_group,
			enabled=1,
		).insert()
