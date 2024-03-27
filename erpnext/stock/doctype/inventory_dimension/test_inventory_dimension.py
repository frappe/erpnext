# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, nowtime

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	CanNotBeChildDoc,
	CanNotBeDefaultDimension,
	DoNotChangeError,
	delete_dimension,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestInventoryDimension(FrappeTestCase):
	def setUp(self):
		prepare_test_data()
		create_store_dimension()

	def test_validate_inventory_dimension(self):
		# Can not be child doc
		inv_dim1 = create_inventory_dimension(
			reference_document="Stock Entry Detail",
			type_of_transaction="Outward",
			dimension_name="Stock Entry",
			apply_to_all_doctypes=0,
			istable=0,
			document_type="Stock Entry",
			do_not_save=True,
		)

		self.assertRaises(CanNotBeChildDoc, inv_dim1.insert)

		inv_dim1 = create_inventory_dimension(
			reference_document="Batch",
			type_of_transaction="Outward",
			dimension_name="Batch",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			do_not_save=True,
		)

		self.assertRaises(CanNotBeDefaultDimension, inv_dim1.insert)

	def test_delete_inventory_dimension(self):
		inv_dim1 = create_inventory_dimension(
			reference_document="Shelf",
			type_of_transaction="Outward",
			dimension_name="From Shelf",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			condition="parent.purpose == 'Material Issue'",
		)

		inv_dim1.save()

		custom_field = frappe.db.get_value(
			"Custom Field", {"fieldname": "from_shelf", "dt": "Stock Entry Detail"}, "name"
		)

		self.assertTrue(custom_field)

		delete_dimension(inv_dim1.name)

		custom_field = frappe.db.get_value(
			"Custom Field", {"fieldname": "from_shelf", "dt": "Stock Entry Detail"}, "name"
		)

		self.assertFalse(custom_field)

	def test_inventory_dimension(self):
		frappe.local.document_wise_inventory_dimensions = {}

		warehouse = "Shelf Warehouse - _TC"
		item_code = "_Test Item"

		inv_dim1 = create_inventory_dimension(
			reference_document="Shelf",
			type_of_transaction="Outward",
			dimension_name="Shelf",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			condition="parent.purpose == 'Material Issue'",
		)

		inv_dim1.reqd = 0
		inv_dim1.save()

		create_inventory_dimension(
			reference_document="Shelf",
			type_of_transaction="Inward",
			dimension_name="To Shelf",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
			condition="parent.purpose == 'Material Receipt'",
		)

		inward = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=5,
			basic_rate=10,
			do_not_save=True,
			purpose="Material Receipt",
		)

		inward.items[0].to_shelf = "Shelf 1"
		inward.save()
		inward.submit()
		inward.load_from_db()

		sle_data = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": inward.name}, ["shelf", "warehouse"], as_dict=1
		)

		self.assertEqual(inward.items[0].to_shelf, "Shelf 1")
		self.assertEqual(sle_data.warehouse, warehouse)
		self.assertEqual(sle_data.shelf, "Shelf 1")

		outward = make_stock_entry(
			item_code=item_code,
			source=warehouse,
			qty=3,
			basic_rate=10,
			do_not_save=True,
			purpose="Material Issue",
		)

		outward.items[0].shelf = "Shelf 1"
		outward.save()
		outward.submit()
		outward.load_from_db()

		sle_shelf = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": outward.name}, "shelf")
		self.assertEqual(sle_shelf, "Shelf 1")

		inv_dim1.load_from_db()
		inv_dim1.apply_to_all_doctypes = 1

		self.assertTrue(inv_dim1.has_stock_ledger())
		self.assertRaises(DoNotChangeError, inv_dim1.save)

	def test_inventory_dimension_for_purchase_receipt_and_delivery_note(self):
		frappe.local.document_wise_inventory_dimensions = {}

		inv_dimension = create_inventory_dimension(
			reference_document="Rack", dimension_name="Rack", apply_to_all_doctypes=1
		)

		self.assertEqual(inv_dimension.type_of_transaction, "Both")
		self.assertEqual(inv_dimension.fetch_from_parent, "Rack")

		create_custom_field(
			"Purchase Receipt", dict(fieldname="rack", label="Rack", fieldtype="Link", options="Rack")
		)

		create_custom_field(
			"Delivery Note", dict(fieldname="rack", label="Rack", fieldtype="Link", options="Rack")
		)

		frappe.reload_doc("stock", "doctype", "purchase_receipt_item")
		frappe.reload_doc("stock", "doctype", "delivery_note_item")

		pr_doc = make_purchase_receipt(qty=2, do_not_submit=True)
		pr_doc.rack = "Rack 1"
		pr_doc.save()
		pr_doc.submit()

		pr_doc.load_from_db()

		self.assertEqual(pr_doc.items[0].rack, "Rack 1")
		sle_rack = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_detail_no": pr_doc.items[0].name, "voucher_type": pr_doc.doctype},
			"rack",
		)

		self.assertEqual(sle_rack, "Rack 1")

		dn_doc = create_delivery_note(qty=2, do_not_submit=True)
		dn_doc.rack = "Rack 1"
		dn_doc.save()
		dn_doc.submit()

		dn_doc.load_from_db()

		self.assertEqual(dn_doc.items[0].rack, "Rack 1")
		sle_rack = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_detail_no": dn_doc.items[0].name, "voucher_type": dn_doc.doctype},
			"rack",
		)

		self.assertEqual(sle_rack, "Rack 1")

	def test_check_standard_dimensions(self):
		create_inventory_dimension(
			reference_document="Project",
			type_of_transaction="Outward",
			dimension_name="Project",
			apply_to_all_doctypes=0,
			document_type="Stock Ledger Entry",
		)

		self.assertFalse(
			frappe.db.get_value("Custom Field", {"fieldname": "project", "dt": "Stock Ledger Entry"}, "name")
		)

	def test_check_mandatory_dimensions(self):
		doc = create_inventory_dimension(
			reference_document="Pallet",
			type_of_transaction="Outward",
			dimension_name="Pallet",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
		)

		doc.reqd = 1
		doc.save()

		self.assertTrue(
			frappe.db.get_value(
				"Custom Field", {"fieldname": "pallet", "dt": "Stock Entry Detail", "reqd": 1}, "name"
			)
		)

		doc.load_from_db
		doc.reqd = 0
		doc.save()

	def test_check_mandatory_depends_on_dimensions(self):
		doc = create_inventory_dimension(
			reference_document="Pallet",
			type_of_transaction="Outward",
			dimension_name="Pallet",
			apply_to_all_doctypes=0,
			document_type="Stock Entry Detail",
		)

		doc.mandatory_depends_on = "t_warehouse"
		doc.save()

		self.assertTrue(
			frappe.db.get_value(
				"Custom Field",
				{"fieldname": "pallet", "dt": "Stock Entry Detail", "mandatory_depends_on": "t_warehouse"},
				"name",
			)
		)

	def test_for_purchase_sales_and_stock_transaction(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		create_inventory_dimension(
			reference_document="Store",
			type_of_transaction="Outward",
			dimension_name="Store",
			apply_to_all_doctypes=1,
		)

		item_code = "Test Inventory Dimension Item"
		create_item(item_code)
		warehouse = create_warehouse("Store Warehouse")

		# Purchase Receipt -> Inward in Store 1
		pr_doc = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, do_not_submit=True
		)

		pr_doc.items[0].store = "Store 1"
		pr_doc.save()
		pr_doc.submit()

		entries = get_voucher_sl_entries(pr_doc.name, ["warehouse", "store", "incoming_rate"])

		self.assertEqual(entries[0].warehouse, warehouse)
		self.assertEqual(entries[0].store, "Store 1")

		# Stock Entry -> Transfer from Store 1 to Store 2
		se_doc = make_stock_entry(
			item_code=item_code, qty=10, from_warehouse=warehouse, to_warehouse=warehouse, do_not_save=True
		)

		se_doc.items[0].store = "Store 1"
		se_doc.items[0].to_store = "Store 2"

		se_doc.save()
		se_doc.submit()

		entries = get_voucher_sl_entries(se_doc.name, ["warehouse", "store", "incoming_rate", "actual_qty"])

		for entry in entries:
			self.assertEqual(entry.warehouse, warehouse)
			if entry.actual_qty > 0:
				self.assertEqual(entry.store, "Store 2")
				self.assertEqual(entry.incoming_rate, 100.0)
			else:
				self.assertEqual(entry.store, "Store 1")

		# Delivery Note -> Outward from Store 2

		dn_doc = create_delivery_note(item_code=item_code, qty=10, warehouse=warehouse, do_not_save=True)

		dn_doc.items[0].store = "Store 2"
		dn_doc.save()
		dn_doc.submit()

		entries = get_voucher_sl_entries(dn_doc.name, ["warehouse", "store", "actual_qty"])

		self.assertEqual(entries[0].warehouse, warehouse)
		self.assertEqual(entries[0].store, "Store 2")
		self.assertEqual(entries[0].actual_qty, -10.0)

		return_dn = make_return_doc("Delivery Note", dn_doc.name)
		return_dn.submit()
		entries = get_voucher_sl_entries(return_dn.name, ["warehouse", "store", "actual_qty"])

		self.assertEqual(entries[0].warehouse, warehouse)
		self.assertEqual(entries[0].store, "Store 2")
		self.assertEqual(entries[0].actual_qty, 10.0)

		se_doc = make_stock_entry(
			item_code=item_code, qty=10, from_warehouse=warehouse, to_warehouse=warehouse, do_not_save=True
		)

		se_doc.items[0].store = "Store 2"
		se_doc.items[0].to_store = "Store 1"

		se_doc.save()
		se_doc.submit()

		return_pr = make_return_doc("Purchase Receipt", pr_doc.name)
		return_pr.submit()
		entries = get_voucher_sl_entries(return_pr.name, ["warehouse", "store", "actual_qty"])

		self.assertEqual(entries[0].warehouse, warehouse)
		self.assertEqual(entries[0].store, "Store 1")
		self.assertEqual(entries[0].actual_qty, -10.0)

	def test_inter_transfer_return_against_inventory_dimension(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt

		data = prepare_data_for_internal_transfer()

		dn_doc = create_delivery_note(
			customer=data.customer,
			company=data.company,
			warehouse=data.from_warehouse,
			target_warehouse=data.to_warehouse,
			qty=5,
			cost_center=data.cost_center,
			expense_account=data.expense_account,
			do_not_submit=True,
		)

		dn_doc.items[0].store = "Inter Transfer Store 1"
		dn_doc.items[0].to_store = "Inter Transfer Store 2"
		dn_doc.save()
		dn_doc.submit()

		for d in get_voucher_sl_entries(dn_doc.name, ["store", "actual_qty"]):
			if d.actual_qty > 0:
				self.assertEqual(d.store, "Inter Transfer Store 2")
			else:
				self.assertEqual(d.store, "Inter Transfer Store 1")

		pr_doc = make_inter_company_purchase_receipt(dn_doc.name)
		pr_doc.items[0].warehouse = data.store_warehouse
		pr_doc.items[0].from_store = "Inter Transfer Store 2"
		pr_doc.items[0].store = "Inter Transfer Store 3"
		pr_doc.save()
		pr_doc.submit()

		for d in get_voucher_sl_entries(pr_doc.name, ["store", "actual_qty"]):
			if d.actual_qty > 0:
				self.assertEqual(d.store, "Inter Transfer Store 3")
			else:
				self.assertEqual(d.store, "Inter Transfer Store 2")

		return_doc = make_return_doc("Purchase Receipt", pr_doc.name)
		return_doc.submit()

		for d in get_voucher_sl_entries(return_doc.name, ["store", "actual_qty"]):
			if d.actual_qty > 0:
				self.assertEqual(d.store, "Inter Transfer Store 2")
			else:
				self.assertEqual(d.store, "Inter Transfer Store 3")

		dn_doc.load_from_db()

		return_doc1 = make_return_doc("Delivery Note", dn_doc.name)
		return_doc1.posting_date = nowdate()
		return_doc1.posting_time = nowtime()
		return_doc1.items[0].target_warehouse = dn_doc.items[0].target_warehouse
		return_doc1.items[0].warehouse = dn_doc.items[0].warehouse
		return_doc1.save()
		return_doc1.submit()

		for d in get_voucher_sl_entries(return_doc1.name, ["store", "actual_qty"]):
			if d.actual_qty > 0:
				self.assertEqual(d.store, "Inter Transfer Store 1")
			else:
				self.assertEqual(d.store, "Inter Transfer Store 2")

	def test_validate_negative_stock_for_inventory_dimension(self):
		frappe.local.inventory_dimensions = {}
		item_code = "Test Negative Inventory Dimension Item"
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
		create_item(item_code)

		inv_dimension = create_inventory_dimension(
			apply_to_all_doctypes=1,
			dimension_name="Inv Site",
			reference_document="Inv Site",
			document_type="Inv Site",
			validate_negative_stock=1,
		)

		warehouse = create_warehouse("Negative Stock Warehouse")

		doc = make_stock_entry(item_code=item_code, source=warehouse, qty=10, do_not_submit=True)
		doc.items[0].inv_site = "Site 1"
		self.assertRaises(frappe.ValidationError, doc.submit)
		doc.reload()
		if doc.docstatus == 1:
			doc.cancel()

		doc = make_stock_entry(item_code=item_code, target=warehouse, qty=10, do_not_submit=True)

		doc.items[0].to_inv_site = "Site 1"
		doc.submit()

		site_name = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": doc.name, "is_cancelled": 0}, fields=["inv_site"]
		)[0].inv_site

		self.assertEqual(site_name, "Site 1")

		doc = make_stock_entry(item_code=item_code, source=warehouse, qty=100, do_not_submit=True)

		doc.items[0].inv_site = "Site 1"
		self.assertRaises(frappe.ValidationError, doc.submit)

		inv_dimension.reload()
		inv_dimension.db_set("validate_negative_stock", 0)
		frappe.local.inventory_dimensions = {}

		doc = make_stock_entry(item_code=item_code, source=warehouse, qty=100, do_not_submit=True)

		doc.items[0].inv_site = "Site 1"
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

		site_name = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": doc.name, "is_cancelled": 0}, fields=["inv_site"]
		)[0].inv_site

		self.assertEqual(site_name, "Site 1")


def get_voucher_sl_entries(voucher_no, fields):
	return frappe.get_all(
		"Stock Ledger Entry", filters={"voucher_no": voucher_no}, fields=fields, order_by="creation"
	)


def create_store_dimension():
	if not frappe.db.exists("DocType", "Store"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Store",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:store_name",
				"fields": [{"label": "Store Name", "fieldname": "store_name", "fieldtype": "Data"}],
				"permissions": [
					{
						"role": "System Manager",
						"permlevel": 0,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	for store in ["Store 1", "Store 2"]:
		if not frappe.db.exists("Store", store):
			frappe.get_doc({"doctype": "Store", "store_name": store}).insert(ignore_permissions=True)


def prepare_test_data():
	if not frappe.db.exists("DocType", "Shelf"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Shelf",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:shelf_name",
				"fields": [{"label": "Shelf Name", "fieldname": "shelf_name", "fieldtype": "Data"}],
				"permissions": [
					{
						"role": "System Manager",
						"permlevel": 0,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	for shelf in ["Shelf 1", "Shelf 2"]:
		if not frappe.db.exists("Shelf", shelf):
			frappe.get_doc({"doctype": "Shelf", "shelf_name": shelf}).insert(ignore_permissions=True)

	create_warehouse("Shelf Warehouse")

	if not frappe.db.exists("DocType", "Rack"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Rack",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:rack_name",
				"fields": [{"label": "Rack Name", "fieldname": "rack_name", "fieldtype": "Data"}],
				"permissions": [
					{
						"role": "System Manager",
						"permlevel": 0,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	for rack in ["Rack 1"]:
		if not frappe.db.exists("Rack", rack):
			frappe.get_doc({"doctype": "Rack", "rack_name": rack}).insert(ignore_permissions=True)

	create_warehouse("Rack Warehouse")

	if not frappe.db.exists("DocType", "Pallet"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Pallet",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:pallet_name",
				"fields": [{"label": "Pallet Name", "fieldname": "pallet_name", "fieldtype": "Data"}],
				"permissions": [
					{
						"role": "System Manager",
						"permlevel": 0,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("DocType", "Inv Site"):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": "Inv Site",
				"module": "Stock",
				"custom": 1,
				"naming_rule": "By fieldname",
				"autoname": "field:site_name",
				"fields": [{"label": "Site Name", "fieldname": "site_name", "fieldtype": "Data"}],
				"permissions": [
					{
						"role": "System Manager",
						"permlevel": 0,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	for site in ["Site 1", "Site 2"]:
		if not frappe.db.exists("Inv Site", site):
			frappe.get_doc({"doctype": "Inv Site", "site_name": site}).insert(ignore_permissions=True)


def create_inventory_dimension(**args):
	args = frappe._dict(args)

	if frappe.db.exists("Inventory Dimension", args.dimension_name):
		return frappe.get_doc("Inventory Dimension", args.dimension_name)

	doc = frappe.new_doc("Inventory Dimension")
	doc.update(args)

	if not args.do_not_save:
		doc.insert(ignore_permissions=True)

	return doc


def prepare_data_for_internal_transfer():
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_internal_supplier
	from erpnext.selling.doctype.customer.test_customer import create_internal_customer
	from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	company = "_Test Company with perpetual inventory"

	customer = create_internal_customer(
		"_Test Internal Customer 3",
		company,
		company,
	)

	supplier = create_internal_supplier(
		"_Test Internal Supplier 3",
		company,
		company,
	)

	for store in ["Inter Transfer Store 1", "Inter Transfer Store 2", "Inter Transfer Store 3"]:
		if not frappe.db.exists("Store", store):
			frappe.get_doc({"doctype": "Store", "store_name": store}).insert(ignore_permissions=True)

	warehouse = create_warehouse("_Test Internal Warehouse New A", company=company)

	to_warehouse = create_warehouse("_Test Internal Warehouse GIT A", company=company)

	pr_doc = make_purchase_receipt(company=company, warehouse=warehouse, qty=10, rate=100, do_not_submit=True)
	pr_doc.items[0].store = "Inter Transfer Store 1"
	pr_doc.submit()

	if not frappe.db.get_value("Company", company, "unrealized_profit_loss_account"):
		account = "Unrealized Profit and Loss - TCP1"
		if not frappe.db.exists("Account", account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Unrealized Profit and Loss",
					"parent_account": "Direct Income - TCP1",
					"company": company,
					"is_group": 0,
					"account_type": "Income Account",
				}
			).insert()

		frappe.db.set_value("Company", company, "unrealized_profit_loss_account", account)

	cost_center = frappe.db.get_value("Company", company, "cost_center") or frappe.db.get_value(
		"Cost Center", {"company": company}, "name"
	)

	expene_account = frappe.db.get_value(
		"Company", company, "stock_adjustment_account"
	) or frappe.db.get_value("Account", {"company": company, "account_type": "Expense Account"}, "name")

	return frappe._dict(
		{
			"from_warehouse": warehouse,
			"to_warehouse": to_warehouse,
			"customer": customer,
			"supplier": supplier,
			"company": company,
			"cost_center": cost_center,
			"expene_account": expene_account,
			"store_warehouse": frappe.db.get_value(
				"Warehouse", {"name": ("like", "Store%"), "company": company}, "name"
			),
		}
	)
