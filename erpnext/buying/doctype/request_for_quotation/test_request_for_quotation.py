# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
	create_supplier_quotation,
	make_supplier_quotation_from_rfq,
)
from erpnext.crm.doctype.opportunity.opportunity import make_request_for_quotation as make_rfq
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.templates.pages.rfq import check_supplier_has_docname_access


class TestRequestforQuotation(FrappeTestCase):
	def test_quote_status(self):
		rfq = make_request_for_quotation()

		self.assertEqual(rfq.get("suppliers")[0].quote_status, "Pending")
		self.assertEqual(rfq.get("suppliers")[1].quote_status, "Pending")

		# Submit the first supplier quotation
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.get("suppliers")[0].supplier)
		sq.submit()

		rfq.update_rfq_supplier_status()  # rfq.get('suppliers')[1].supplier)

		self.assertEqual(rfq.get("suppliers")[0].quote_status, "Received")
		self.assertEqual(rfq.get("suppliers")[1].quote_status, "Pending")

	def test_make_supplier_quotation(self):
		rfq = make_request_for_quotation()

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.get("suppliers")[0].supplier)
		sq.submit()

		sq1 = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.get("suppliers")[1].supplier)
		sq1.submit()

		self.assertEqual(sq.supplier, rfq.get("suppliers")[0].supplier)
		self.assertEqual(sq.get("items")[0].request_for_quotation, rfq.name)
		self.assertEqual(sq.get("items")[0].item_code, "_Test Item")
		self.assertEqual(sq.get("items")[0].qty, 5)

		self.assertEqual(sq1.supplier, rfq.get("suppliers")[1].supplier)
		self.assertEqual(sq1.get("items")[0].request_for_quotation, rfq.name)
		self.assertEqual(sq1.get("items")[0].item_code, "_Test Item")
		self.assertEqual(sq1.get("items")[0].qty, 5)

	def test_make_supplier_quotation_with_special_characters(self):
		frappe.delete_doc_if_exists("Supplier", "_Test Supplier '1", force=1)
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = "_Test Supplier '1"
		supplier.supplier_group = "_Test Supplier Group"
		supplier.insert()

		rfq = make_request_for_quotation(supplier_data=supplier_wt_appos)

		sq = make_supplier_quotation_from_rfq(
			rfq.name, for_supplier=supplier_wt_appos[0].get("supplier")
		)
		sq.submit()

		frappe.form_dict.name = rfq.name

		self.assertEqual(check_supplier_has_docname_access(supplier_wt_appos[0].get("supplier")), True)

		# reset form_dict
		frappe.form_dict.name = None

	def test_make_supplier_quotation_from_portal(self):
		rfq = make_request_for_quotation()
		rfq.get("items")[0].rate = 100
		rfq.supplier = rfq.suppliers[0].supplier
		supplier_quotation_name = create_supplier_quotation(rfq)

		supplier_quotation_doc = frappe.get_doc("Supplier Quotation", supplier_quotation_name)

		self.assertEqual(supplier_quotation_doc.supplier, rfq.get("suppliers")[0].supplier)
		self.assertEqual(supplier_quotation_doc.get("items")[0].request_for_quotation, rfq.name)
		self.assertEqual(supplier_quotation_doc.get("items")[0].item_code, "_Test Item")
		self.assertEqual(supplier_quotation_doc.get("items")[0].qty, 5)
		self.assertEqual(supplier_quotation_doc.get("items")[0].amount, 500)

	def test_make_multi_uom_supplier_quotation(self):
		item_code = "_Test Multi UOM RFQ Item"
		if not frappe.db.exists("Item", item_code):
			item = make_item(item_code, {"stock_uom": "_Test UOM"})
			row = item.append("uoms", {"uom": "Kg", "conversion_factor": 2})
			row.db_update()

		rfq = make_request_for_quotation(
			item_code="_Test Multi UOM RFQ Item", uom="Kg", conversion_factor=2
		)
		rfq.get("items")[0].rate = 100
		rfq.supplier = rfq.suppliers[0].supplier

		self.assertEqual(rfq.items[0].stock_qty, 10)

		supplier_quotation_name = create_supplier_quotation(rfq)
		supplier_quotation = frappe.get_doc("Supplier Quotation", supplier_quotation_name)

		self.assertEqual(supplier_quotation.items[0].qty, 5)
		self.assertEqual(supplier_quotation.items[0].stock_qty, 10)

	def test_make_rfq_from_opportunity(self):
		opportunity = make_opportunity(with_items=1)
		supplier_data = get_supplier_data()
		rfq = make_rfq(opportunity.name)

		self.assertEqual(len(rfq.get("items")), len(opportunity.get("items")))
		rfq.message_for_supplier = "Please supply the specified items at the best possible rates."

		for item in rfq.items:
			item.warehouse = "_Test Warehouse - _TC"

		for data in supplier_data:
			rfq.append("suppliers", data)

		rfq.status = "Draft"
		rfq.submit()


def make_request_for_quotation(**args):
	"""
	:param supplier_data: List containing supplier data
	"""
	args = frappe._dict(args)
	supplier_data = args.get("supplier_data") if args.get("supplier_data") else get_supplier_data()
	rfq = frappe.new_doc("Request for Quotation")
	rfq.transaction_date = nowdate()
	rfq.status = "Draft"
	rfq.company = "_Test Company"
	rfq.message_for_supplier = "Please supply the specified items at the best possible rates."

	for data in supplier_data:
		rfq.append("suppliers", data)

	rfq.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"description": "_Test Item",
			"uom": args.uom or "_Test UOM",
			"stock_uom": args.stock_uom or "_Test UOM",
			"qty": args.qty or 5,
			"conversion_factor": args.conversion_factor or 1.0,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"schedule_date": nowdate(),
		},
	)

	rfq.submit()

	return rfq


def get_supplier_data():
	return [
		{"supplier": "_Test Supplier", "supplier_name": "_Test Supplier"},
		{"supplier": "_Test Supplier 1", "supplier_name": "_Test Supplier 1"},
	]


supplier_wt_appos = [
	{
		"supplier": "_Test Supplier '1",
		"supplier_name": "_Test Supplier '1",
	}
]
