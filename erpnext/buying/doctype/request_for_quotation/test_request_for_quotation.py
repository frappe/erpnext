# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from urllib.parse import urlparse

import frappe
from frappe.tests.utils import FrappeTestCase, if_app_installed,change_settings
from frappe.utils import nowdate

from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
	RequestforQuotation,
	create_supplier_quotation,
	get_pdf,
	make_supplier_quotation_from_rfq,
)
from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.templates.pages.rfq import check_supplier_has_docname_access


class TestRequestforQuotation(FrappeTestCase):
	def test_rfq_qty(self):
		rfq = make_request_for_quotation(qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			rfq.save()

		# No error with qty=1
		rfq.items[0].qty = 1
		rfq.save()
		self.assertEqual(rfq.items[0].qty, 1)

	def setUp(self):
		# Create dummy supplier
		self.supplier = frappe.get_doc(
			{"doctype": "Supplier", "supplier_name": "Test", "supplier_type": "Company"}
		).insert(ignore_if_duplicate=True)

		item = make_item("Test", {"stock_uom": "Nos"})
		self.rfq = make_request_for_quotation(
			item_code=item.name,
			supplier_data=[
				{
					"supplier": self.supplier.name,
					"supplier_name": self.supplier.supplier_name,
					"email_id": "123_testrfquser@example.com",
				}
			],
		)

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

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier_wt_appos[0].get("supplier"))
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

		rfq = make_request_for_quotation(item_code="_Test Multi UOM RFQ Item", uom="Kg", conversion_factor=2)
		rfq.get("items")[0].rate = 100
		rfq.supplier = rfq.suppliers[0].supplier

		self.assertEqual(rfq.items[0].stock_qty, 10)

		supplier_quotation_name = create_supplier_quotation(rfq)
		supplier_quotation = frappe.get_doc("Supplier Quotation", supplier_quotation_name)

		self.assertEqual(supplier_quotation.items[0].qty, 5)
		self.assertEqual(supplier_quotation.items[0].stock_qty, 10)

	@if_app_installed("erpnext_crm")
	def test_make_rfq_from_opportunity(self):
		from erpnext_crm.erpnext_crm.doctype.opportunity.opportunity import (
			make_request_for_quotation as make_rfq,
		)
		from erpnext_crm.erpnext_crm.doctype.opportunity.test_opportunity import make_opportunity

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

	def test_get_link(self):
		rfq = make_request_for_quotation()
		parsed_link = urlparse(rfq.get_link())
		self.assertEqual(parsed_link.path, f"/rfq/{rfq.name}")

	def test_get_pdf(self):
		rfq = make_request_for_quotation()
		get_pdf(rfq.name, rfq.get("suppliers")[0].supplier)
		self.assertEqual(frappe.local.response.type, "pdf")

	def test_portal_user_with_new_supplier(self):
		supplier_doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Test Supplier for RFQ",
				"supplier_group": "_Test Supplier Group",
			}
		).insert()

		self.assertFalse(supplier_doc.portal_users)

		rfq = make_request_for_quotation(
			supplier_data=[
				{
					"supplier": supplier_doc.name,
					"supplier_name": supplier_doc.supplier_name,
					"email_id": "123_testrfquser@example.com",
				}
			],
			do_not_submit=True,
		)
		for rfq_supplier in rfq.suppliers:
			rfq.update_supplier_contact(rfq_supplier, rfq.get_link())

		supplier_doc.reload()
		self.assertTrue(supplier_doc.portal_users[0].user)

	def test_send_supplier_emails_runs_TC_B_193(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import send_supplier_emails

		send_supplier_emails(self.rfq.name)

		communications = frappe.get_all(
			"Communication",
			filters={"reference_doctype": "Request for Quotation", "reference_name": self.rfq.name},
		)
		self.assertGreaterEqual(len(communications), 1)

	def test_get_supplier_email_preview_TC_B_194(self):
		item_code = "_Test Item"
		supplier_name = "_Test Supplier"
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"stock_uom": "Nos"})
		if not frappe.db.exists({"doctype": "Supplier", "supplier_name": supplier_name}):
			supplier_doc = frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": "_Test Supplier",
					"supplier_group": "_Test Supplier Group",
				}
			).insert()
		else:
			supplier_doc = frappe.get_doc("Supplier", supplier_name)
		rfq = make_request_for_quotation(
			item_code=item_code,
			supplier_data=[
				{
					"supplier": supplier_doc.name,
					"supplier_name": supplier_doc.supplier_name,
					"email_id": "testrfquser@example.com",
				}
			],
		)
		email_template = frappe.get_doc(
			{"doctype": "Email Template", "__newname": "Test", "subject": "Test", "response": "test"}
		).insert()
		rfq.email_template = email_template.name
		preview = rfq.get_supplier_email_preview(supplier_doc.name)
		self.assertIn(email_template.response, preview["message"])

	def test_get_supplier_tag_TC_B_195(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import get_supplier_tag

		tags = get_supplier_tag()
		self.assertIsInstance(tags, list)

	def test_get_rfq_containing_supplier_TC_B_196(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
			get_rfq_containing_supplier,
		)

		filters = {
			"company": self.rfq.company,
			"supplier": self.supplier.name,
			"transaction_date": self.rfq.transaction_date,
		}

		rfqs = get_rfq_containing_supplier("Request for Quotation", "", "name", 0, 10, filters)

		self.assertTrue(any(r["name"] == self.rfq.name for r in rfqs))

	def test_get_list_context_coverage_TC_B_197(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import get_list_context

		context = get_list_context()
		self.assertEqual(context["title"], "Request for Quotation")
		self.assertTrue(context["show_sidebar"])
		self.assertTrue(context["no_breadcrumbs"])

	def test_supplier_rfq_mail_TC_B_198(self):
		item_code = "_Test Item"
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"stock_uom": "Nos"})
		supplier_doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Test Supplier1",
			}
		).insert()
		rfq = make_request_for_quotation(
			item_code=item_code,
			supplier_data=[
				{
					"supplier": supplier_doc.name,
					"supplier_name": supplier_doc.supplier_name,
					"email_id": "testrfquser@example.com",
				}
			],
			do_not_submit=True,
		)
		rfq.email_template = "Dispatch Notification"

		data = {"supplier": "Test Supplier", "supplier_name": "Test Supplier1", "contact": None}

		update_password_link = "http://example.com/set-password"
		rfq_link = "http://example.com/submit-quotation"

		preview = rfq.supplier_rfq_mail(data, update_password_link, rfq_link, preview=True)

		self.assertIn("Test Supplier1", preview["message"])
		self.assertIn("Set Password", preview["message"])
		self.assertIn("Test Supplier Name", preview["subject"])

	def test_on_cancel_TC_B_199(self):
		rfq = make_request_for_quotation()
		rfq.cancel()
		cancelled_rfq = frappe.get_doc("Request for Quotation", rfq.name)
		self.assertEqual(cancelled_rfq.status, "Cancelled")

	def test_get_attachments_TC_B_200(self):
		rfq = make_request_for_quotation()

		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "test.txt",
				"attached_to_doctype": "Request for Quotation",
				"attached_to_name": rfq.name,
				"content": "Hello, world!",
			}
		).insert(ignore_permissions=True)

		rfq.reload()
		attachment_names = rfq.get_attachments()

		self.assertIn(file.name, attachment_names)

	def test_get_item_from_material_requests_based_on_supplier_TC_B_201(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
			get_item_from_material_requests_based_on_supplier,
		)

		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Test Supplier"}).insert(
			ignore_if_duplicate=True, ignore_permissions=True
		)

		gst_hsn_code = (
			frappe.get_doc({"doctype": "GST HSN Code", "hsn_code": "110011"})
			.insert(ignore_if_duplicate=True, ignore_permissions=True)
			.name
		)

		item_code = "_Test Item Supplier Coverage"
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"stock_uom": "Nos",
				"item_group": "All Item Groups",
				"gst_hsn_code": gst_hsn_code,
				"is_stock_item": 1,
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		item = frappe.get_doc("Item", item.name)
		if not any(row.supplier == supplier.name for row in item.supplier_items):
			item.append("supplier_items", {"supplier": supplier.name})
			item.save()

		warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "_Test Stores"}).insert(
			ignore_if_duplicate=True
		)

		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"items": [
					{
						"item_code": item.name,
						"qty": 10,
						"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
						"warehouse": warehouse.name,
					}
				],
			}
		).insert(ignore_permissions=True)
		mr.submit()

		rfq_doc = get_item_from_material_requests_based_on_supplier(supplier.name)

		self.assertIsNotNone(rfq_doc)
		self.assertEqual(rfq_doc.doctype, "Request for Quotation")
		self.assertEqual(len(rfq_doc.items), 1)
		self.assertEqual(rfq_doc.items[0].item_code, item.name)
		self.assertEqual(rfq_doc.items[0].material_request, mr.name)

	def test_send_email_TC_B_202(self):
		from unittest.mock import patch

		item_code = "_Test Item"
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"stock_uom": "Nos"})

		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Email Test Supplier"}).insert(
			ignore_if_duplicate=True, ignore_permissions=True
		)

		rfq = make_request_for_quotation(
			item_code=item_code,
			supplier_data=[
				{
					"supplier": supplier.name,
					"supplier_name": supplier.supplier_name,
					"email_id": "testrfquser@example.com",
				}
			],
			do_not_submit=True,
		)
		rfq.email_template = "Dispatch Notification"

		data = frappe._dict(
			{
				"supplier": supplier.name,
				"supplier_name": supplier.supplier_name,
				"email_id": "testrfquser@example.com",
				"contact": None,
			}
		)

		update_password_link = "http://example.com/set-password"
		rfq_link = "http://example.com/submit-quotation"

		with patch("erpnext.buying.doctype.request_for_quotation.request_for_quotation.make") as mock_make:
			rfq.supplier_rfq_mail(data, update_password_link, rfq_link, preview=False)

			mock_make.assert_called_once()
			args, kwargs = mock_make.call_args
			self.assertIn("subject", kwargs)
			self.assertIn("recipients", kwargs)
			self.assertEqual(kwargs["recipients"], data.email_id)

	@change_settings("Buying Settings", {"allow_zero_qty_in_request_for_quotation": 1})
	def test_supplier_quotation_from_zero_qty_rfq(self):
		rfq = make_request_for_quotation(qty=0)
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.get("suppliers")[0].supplier)

		self.assertEqual(len(sq.items), 1)
		self.assertEqual(sq.items[0].qty, 0)
		self.assertEqual(sq.items[0].item_code, rfq.items[0].item_code)

	@change_settings(
		"Buying Settings",
		{
			"allow_zero_qty_in_request_for_quotation": 1,
			"allow_zero_qty_in_supplier_quotation": 1,
		},
	)
	def test_supplier_quotation_from_zero_qty_rfq_in_portal(self):
		rfq = make_request_for_quotation(qty=0)
		rfq.supplier = rfq.suppliers[0].supplier
		sq_name = create_supplier_quotation(rfq)

		sq = frappe.get_doc("Supplier Quotation", sq_name)
		self.assertEqual(len(sq.items), 1)
		self.assertEqual(sq.items[0].qty, 0)
		self.assertEqual(sq.items[0].item_code, rfq.items[0].item_code)

def make_request_for_quotation(**args) -> "RequestforQuotation":
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
			"qty": args.qty if args.qty is not None else 5,
			"conversion_factor": args.conversion_factor or 1.0,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"schedule_date": nowdate(),
		},
	)

	if not args.do_not_save:
		rfq.insert()
		if not args.do_not_submit:
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
