# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.queries import item_query

test_dependencies = ["Item", "Customer", "Supplier"]


def create_party_specific_item(**args):
	psi = frappe.new_doc("Party Specific Item")
	psi.party_type = args.get("party_type")
	psi.party = args.get("party")
	psi.restrict_based_on = args.get("restrict_based_on")
	psi.based_on_value = args.get("based_on_value")
	psi.insert()


class TestPartySpecificItem(FrappeTestCase):
	def setUp(self):
		self.customer = frappe.get_last_doc("Customer")
		self.supplier = frappe.get_last_doc("Supplier")
		self.item = frappe.get_last_doc("Item")

	def test_item_query_for_customer(self):
		create_party_specific_item(
			party_type="Customer",
			party=self.customer.name,
			restrict_based_on="Item",
			based_on_value=self.item.name,
		)
		filters = {"is_sales_item": 1, "customer": self.customer.name}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		for item in items:
			self.assertEqual(item[0], self.item.name)

	def test_item_query_for_supplier(self):
		create_party_specific_item(
			party_type="Supplier",
			party=self.supplier.name,
			restrict_based_on="Item Group",
			based_on_value=self.item.item_group,
		)
		filters = {"supplier": self.supplier.name, "is_purchase_item": 1}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		for item in items:
			self.assertEqual(item[2], self.item.item_group)

	def test_blocks_disallowed_items_after_party_change(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		for party_type, party, make_order in (
			("Customer", "_Test Customer 2", make_sales_order),
			("Supplier", "_Test Supplier 1", create_purchase_order),
		):
			with self.subTest(party_type=party_type):
				create_party_specific_item(
					party_type=party_type,
					party=party,
					restrict_based_on="Item Group",
					based_on_value="_Test Item Group Desktops",
				)
				order = make_order(do_not_submit=True)
				order.set(party_type.lower(), party)
				self.assertRaisesRegex(frappe.ValidationError, "is not allowed for", order.save)

	def test_allows_linked_return_of_disallowed_item(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		invoice = create_sales_invoice(customer="_Test Customer 1", qty=1)
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer 1",
			restrict_based_on="Item Group",
			based_on_value="_Test Item Group Desktops",
		)
		credit_note = make_return_doc("Sales Invoice", invoice.name)
		unlinked_row = credit_note.append("items", credit_note.items[0].as_dict())
		unlinked_row.name = None
		unlinked_row.sales_invoice_item = None
		self.assertRaisesRegex(frappe.ValidationError, "is not allowed for", credit_note.insert)

		credit_note.remove(unlinked_row)
		credit_note.insert()

		standalone_note = frappe.copy_doc(credit_note)
		standalone_note.return_against = None
		self.assertRaisesRegex(frappe.ValidationError, "is not allowed for", standalone_note.insert)
