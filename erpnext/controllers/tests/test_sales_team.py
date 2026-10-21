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
		frappe.db.set_value("Sales Person", self.disabled_person.name, "enabled", 0)

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
