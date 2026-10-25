# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.controllers.queries import item_query
from erpnext.tests.utils import ERPNextTestSuite


def create_party_specific_item(**args):
	psi = frappe.new_doc("Party Specific Item")
	psi.party_type = args.get("party_type")
	psi.party = args.get("party")
	psi.restrict_based_on = args.get("restrict_based_on")
	psi.based_on_value = args.get("based_on_value")
	psi.insert()


def create_supplier(supplier_name):
	if frappe.db.exists("Supplier", supplier_name):
		return frappe.get_doc("Supplier", supplier_name)

	return frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": "Services",
			"supplier_type": "Company",
		}
	).insert()


def create_item(item_code, item_group="Products"):
	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"description": item_code,
			"item_group": item_group,
			"is_purchase_item": 1,
		}
	).insert()


class TestPartySpecificItem(ERPNextTestSuite):
	def test_template_item_rule_covers_variant(self):
		from erpnext.controllers.item_variant import create_variant
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		template = make_item(
			"_Test Party Specific Template",
			{"has_variants": 1, "attributes": [{"attribute": "Test Size"}]},
		)
		variant = create_variant(template.name, {"Test Size": "Small"}).insert()
		other_item = create_item("_Test Party Specific Other Item").name
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Item",
			based_on_value=template.name,
		)

		self.assertIn(variant.name, search_items(variant.name, {"customer": "_Test Customer"}))
		self.assertNotIn(other_item, search_items(other_item, {"customer": "_Test Customer"}))
		self.assertIn(variant.name, search_items(variant.name, {"customer": "_Test Customer 2"}))
		make_sales_order(customer="_Test Customer", item_code=variant.name, do_not_submit=True)
		make_sales_order(customer="_Test Customer 2", item_code=variant.name, do_not_submit=True)
		with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Customer"):
			make_sales_order(customer="_Test Customer", item_code=other_item, do_not_submit=True)

	def test_item_query_for_customer(self):
		customer = "_Test Customer With Template"
		item = "_Test Item"

		create_party_specific_item(
			party_type="Customer",
			party=customer,
			restrict_based_on="Item",
			based_on_value=item,
		)
		filters = {"is_sales_item": 1, "customer": customer}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		self.assertIn(item, flatten(items))

	def test_item_query_for_supplier(self):
		supplier = "_Test Supplier With Template 1"
		item = "_Test Item Group"

		create_party_specific_item(
			party_type="Supplier",
			party=supplier,
			restrict_based_on="Item Group",
			based_on_value=item,
		)
		filters = {"supplier": supplier, "is_purchase_item": 1}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		self.assertIn(item, flatten(items))

	def test_item_query_for_supplier_with_item_restricted_to_multiple_suppliers(self):
		item = f"Party Specific Item {frappe.generate_hash(length=8)}"
		supplier1 = f"Party Specific Supplier {frappe.generate_hash(length=8)}"
		supplier2 = f"Party Specific Supplier {frappe.generate_hash(length=8)}"

		create_item(item)
		create_supplier(supplier1)
		create_supplier(supplier2)

		for supplier in (supplier1, supplier2):
			create_party_specific_item(
				party_type="Supplier",
				party=supplier,
				restrict_based_on="Item",
				based_on_value=item,
			)

		items = item_query(
			doctype="Item",
			txt=item,
			searchfield="name",
			start=0,
			page_len=20,
			filters={"supplier": supplier1, "is_purchase_item": 1},
			as_dict=False,
		)
		self.assertIn(item, flatten(items))

	def test_party_group(self):
		customer = "_Test Customer With Template"
		item = "_Test Item"
		# a rule on a parent group must also cover a customer sitting in its sub-group
		parent_group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "_Test Party Specific Parent Group",
				"parent_customer_group": "All Customer Groups",
				"is_group": 1,
			}
		).insert()
		sub_group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "_Test Party Specific Sub Group",
				"parent_customer_group": parent_group.name,
			}
		).insert()
		frappe.set_value("Customer", customer, "customer_group", sub_group.name)

		other_item = create_item("_Test Party Specific Group Other Item").name
		create_party_specific_item(
			party_type="Customer Group",
			party=parent_group.name,
			restrict_based_on="Item",
			based_on_value=item,
		)
		self.assertIn(item, search_items(item, {"customer": customer}))
		# the ancestor rule must actually restrict the customer, not just allow its item
		self.assertNotIn(other_item, search_items(other_item, {"customer": customer}))

	def test_party_sees_only_items_from_its_rules(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		brand_item = create_item("_Test Party Specific Brand Item").name
		frappe.db.set_value("Item", brand_item, "brand", "_Test Brand")
		listed_item = create_item("_Test Party Specific Listed Item").name
		other_item = create_item("_Test Party Specific Other Item").name
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Brand",
			based_on_value="_Test Brand",
		)
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Item",
			based_on_value=listed_item,
		)

		for item, allowed in ((brand_item, True), (listed_item, True), (other_item, False)):
			with self.subTest(item=item):
				self.assertEqual(item in search_items(item, {"customer": "_Test Customer"}), allowed)
				self.assertIn(item, search_items(item, {"customer": "_Test Customer 2"}))

		make_sales_order(customer="_Test Customer", item_code=listed_item, do_not_submit=True)
		make_sales_order(customer="_Test Customer 2", item_code=other_item, do_not_submit=True)
		with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Customer"):
			make_sales_order(customer="_Test Customer", item_code=other_item, do_not_submit=True)

	def test_item_group_rule_covers_sub_groups(self):
		parent_group = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "_Test Party Specific Parent Group",
				"parent_item_group": "All Item Groups",
				"is_group": 1,
			}
		).insert()
		sub_group = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "_Test Party Specific Sub Group",
				"parent_item_group": parent_group.name,
			}
		).insert()
		item = create_item("_Test Party Specific Sub Group Item", sub_group.name).name
		other_item = create_item("_Test Party Specific Other Item").name
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Item Group",
			based_on_value=parent_group.name,
		)

		for item_code, allowed in ((item, True), (other_item, False)):
			with self.subTest(item=item_code):
				self.assertEqual(
					item_code in search_items(item_code, {"customer": "_Test Customer"}), allowed
				)

	def test_customer_change_revalidates_items_on_save_and_submit(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer 2",
			restrict_based_on="Item",
			based_on_value=create_item("_Test Party Specific Other Item").name,
		)
		order = make_sales_order(do_not_submit=True)
		for action in ("save", "submit"):
			with self.subTest(action=action):
				order.reload()
				order.customer = "_Test Customer 2"
				with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Customer"):
					getattr(order, action)()
		order.reload().submit()
		self.assertEqual(order.docstatus, 1)

	def test_supplier_change_revalidates_items(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		other_supplier = create_supplier("_Test Party Specific Other Supplier")
		create_party_specific_item(
			party_type="Supplier",
			party=other_supplier.name,
			restrict_based_on="Item",
			based_on_value=create_item("_Test Party Specific Other Item").name,
		)
		order = create_purchase_order(do_not_submit=True)
		for action in ("save", "submit"):
			with self.subTest(action=action):
				order.reload()
				order.supplier = other_supplier.name
				with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Supplier"):
					getattr(order, action)()
		order.reload().submit()
		self.assertEqual(order.docstatus, 1)

	def test_sales_user_cannot_bypass_rules_they_cannot_read(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer 2",
			restrict_based_on="Item",
			based_on_value=create_item("_Test Party Specific Other Item").name,
		)
		user = create_user("party-specific-sales@example.com", "Sales User")
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Party Specific Item", "read"))
			order = make_sales_order(do_not_submit=True)
			order.customer = "_Test Customer 2"
			with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Customer"):
				order.save()

	def test_linked_returns_allow_items_restricted_after_sale_or_purchase(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		allowed_item = create_item("_Test Party Specific Other Item").name
		for party_type, make_invoice in (
			("Customer", create_sales_invoice),
			("Supplier", make_purchase_invoice),
		):
			with self.subTest(party_type=party_type):
				invoice = make_invoice(qty=1)
				create_party_specific_item(
					party_type=party_type,
					party=invoice.get(frappe.scrub(party_type)),
					restrict_based_on="Item",
					based_on_value=allowed_item,
				)
				note = make_return_doc(invoice.doctype, invoice.name)
				extra_row = note.append("items", note.items[0].as_dict())
				extra_row.name = None
				extra_row.set(frappe.scrub(invoice.doctype) + "_item", None)
				with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for"):
					note.insert()
				note.remove(extra_row)
				note.insert().submit()
				self.assertEqual(note.docstatus, 1)
				standalone_note = frappe.copy_doc(note)
				standalone_note.return_against = None
				with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for"):
					standalone_note.insert()

	def test_opportunity_enforces_party_rules(self):
		from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity

		allowed_item = create_item("_Test Party Specific Opportunity Allowed Item").name
		other_item = create_item("_Test Party Specific Opportunity Other Item").name
		create_party_specific_item(
			party_type="Customer",
			party="_Test Customer",
			restrict_based_on="Item",
			based_on_value=allowed_item,
		)
		make_opportunity(with_items=True, customer="_Test Customer", item_code=allowed_item)
		with self.assertRaisesRegex(frappe.ValidationError, "is not allowed for Customer"):
			make_opportunity(with_items=True, customer="_Test Customer", item_code=other_item)


def search_items(txt, filters):
	return flatten(
		item_query(
			doctype="Item", txt=txt, searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
	)


def flatten(lst):
	result = []
	for item in lst:
		if isinstance(item, tuple):
			result.extend(flatten(item))
		else:
			result.append(item)
	return result
