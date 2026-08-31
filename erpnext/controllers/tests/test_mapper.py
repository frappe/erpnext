import json
import unittest

import frappe
import frappe.utils
from frappe.model import mapper
from frappe.test_runner import make_test_records
from frappe.utils import add_months, nowdate


class TestMapper(unittest.TestCase):
	def test_map_docs(self):
		"""Test mapping of multiple source docs on a single target doc"""

		make_test_records("Item")
		items = ["_Test Item", "_Test Item 2", "_Test FG Item"]

		# Make source docs (quotations) and a target doc (sales order)
		qtn1, item_list_1 = self.make_quotation(items, "_Test Customer")
		qtn2, item_list_2 = self.make_quotation(items, "_Test Customer")
		so, item_list_3 = self.make_sales_order()

		# Map source docs to target with corresponding mapper method
		method = "erpnext.selling.doctype.quotation.quotation.make_sales_order"
		updated_so = mapper.map_docs(method, json.dumps([qtn1.name, qtn2.name]), so)

		# Assert that all inserted items are present in updated sales order
		src_items = item_list_1 + item_list_2 + item_list_3
		self.assertEqual(set(d for d in src_items), set(d.item_code for d in updated_so.items))

	def test_get_items_from_is_idempotent(self):
		"""Selecting the same source document twice must not duplicate rows in the target.

		"Get Items From" hands the in-progress document back to the mapper as `target_doc`.
		Its rows are unsaved, so the mappers' pending-qty queries (submitted documents only)
		cannot see them -- every mapper has to discount them explicitly.
		"""
		for label, make_source, method in self.idempotency_cases():
			with self.subTest(label):
				source = make_source()
				target = frappe.get_attr(method)(source.name)
				mapped_rows = len(target.items)
				self.assertTrue(mapped_rows, f"{label}: nothing was mapped")

				target = frappe.get_attr(method)(source.name, target)
				self.assertEqual(len(target.items), mapped_rows, f"{label}: rows were duplicated")

	def idempotency_cases(self):
		"""(label, source factory, mapper method) for every "Get Items From" button.

		Quotation -> Sales Invoice is absent: Sales Invoice Item keeps no reference to the
		Quotation row, so there is nothing to deduplicate on.
		"""
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.doctype.supplier_quotation.test_supplier_quotation import (
			test_records as supplier_quotation_records,
		)
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		def make_supplier_quotation():
			return frappe.copy_doc(supplier_quotation_records[0]).submit()

		return [
			(
				"Quotation -> Sales Order",
				lambda: make_quotation(),
				"erpnext.selling.doctype.quotation.quotation.make_sales_order",
			),
			(
				"Sales Order -> Sales Invoice",
				lambda: make_sales_order(),
				"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			),
			(
				"Sales Order -> Delivery Note",
				lambda: make_sales_order(),
				"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			),
			(
				"Delivery Note -> Sales Invoice",
				lambda: create_delivery_note(),
				"erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
			),
			(
				"Material Request -> Purchase Order",
				lambda: make_material_request(),
				"erpnext.stock.doctype.material_request.material_request.make_purchase_order",
			),
			(
				"Supplier Quotation -> Purchase Order",
				make_supplier_quotation,
				"erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
			),
			(
				"Purchase Order -> Purchase Receipt",
				lambda: create_purchase_order(),
				"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
			),
			(
				"Purchase Order -> Purchase Invoice",
				lambda: create_purchase_order(),
				"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
			),
			(
				"Purchase Receipt -> Purchase Invoice",
				lambda: make_purchase_receipt(),
				"erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
			),
			(
				"Purchase Invoice -> Purchase Receipt",
				lambda: make_purchase_invoice(),
				"erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_purchase_receipt",
			),
		]

	def make_quotation(self, item_list, customer):
		qtn = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer,
				"order_type": "Sales",
				"transaction_date": nowdate(),
				"valid_till": add_months(nowdate(), 1),
			}
		)
		for item in item_list:
			qtn.append("items", {"qty": "2", "item_code": item})

		qtn.submit()
		return qtn, item_list

	def make_sales_order(self):
		item = frappe.get_doc(
			{
				"base_amount": 1000.0,
				"base_rate": 100.0,
				"description": "CPU",
				"doctype": "Sales Order Item",
				"item_code": "_Test Item",
				"item_name": "CPU",
				"parentfield": "items",
				"qty": 10.0,
				"rate": 100.0,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "_Test UOM",
				"conversion_factor": 1.0,
				"uom": "_Test UOM",
			}
		)
		so = frappe.get_doc(frappe.get_test_records("Sales Order")[0])
		so.insert(ignore_permissions=True)
		return so, [item.item_code]
