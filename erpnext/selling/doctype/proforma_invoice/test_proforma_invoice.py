# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.pricing_rule.test_pricing_rule import make_pricing_rule
from erpnext.accounts.services.child_item_update import update_child_qty_rate
from erpnext.selling.doctype.proforma_invoice.proforma_invoice import (
	get_sales_order_items,
	make_proforma_invoice,
	send_proforma_email,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite, make_email_template


class TestProformaInvoice(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Selling Settings", "enable_proforma_invoice", 1)

	def create_proforma(self, sales_order, lines, **kwargs):
		items = [{"so_detail": so_detail, "qty": qty} for so_detail, qty in lines]
		name = make_proforma_invoice(sales_order.name, json.dumps(items), **kwargs)
		return frappe.get_doc("Proforma Invoice", name)

	def make_draft_proforma(self, sales_order, **item):
		return frappe.new_doc("Proforma Invoice", sales_order=sales_order.name, items=[item]).insert()

	def test_partial_proforma_is_non_blocking(self):
		"""A proforma must not touch delivery/billing or the source Sales Order."""
		sales_order = make_sales_order(qty=10)
		so_detail = sales_order.items[0].name

		proforma = self.create_proforma(sales_order, [(so_detail, 4)])

		self.assertEqual(proforma.status, "Issued")
		self.assertEqual(proforma.docstatus, 1)
		self.assertTrue(proforma.proforma_pdf, "PDF should be generated and attached")

		sales_order.reload()
		item = sales_order.items[0]
		# fulfillment untouched
		self.assertEqual(flt(item.delivered_qty), 0)
		self.assertEqual(flt(item.billed_amt), 0)
		self.assertEqual(flt(sales_order.per_delivered), 0)
		self.assertEqual(flt(sales_order.per_billed), 0)
		# ordered qty untouched (in-memory SO copy never persisted)
		self.assertEqual(flt(item.qty), 10)

	def test_taxes_scale_to_partial_qty(self):
		sales_order = make_sales_order(qty=10, do_not_submit=True)
		sales_order.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account CST - _TC",
				"description": "CST",
				"rate": 10,
			},
		)
		sales_order.submit()

		# full order: net 1000 + 10% tax = 1100
		self.assertEqual(flt(sales_order.grand_total), 1100)

		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 4)])
		# partial (4 of 10): net 400 + 10% tax = 440
		self.assertEqual(flt(proforma.grand_total), 440)

	def test_fixed_discount_and_actual_charges_scale_to_partial_qty(self):
		sales_order = make_sales_order(qty=10, do_not_submit=True)  # rate 100
		sales_order.apply_discount_on = "Net Total"
		sales_order.discount_amount = 200
		sales_order.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "_Test Account CST - _TC",
				"description": "Freight",
				"tax_amount": 500,
			},
		)
		sales_order.submit()

		# full order: 1000 - 200 discount + 500 freight = 1300
		self.assertEqual(flt(sales_order.grand_total), 1300)

		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 5)])
		# half the order: 500 - 100 discount + 250 freight = 650
		self.assertEqual(flt(proforma.grand_total), 650)

	def test_pricing_rule_discount_is_kept(self):
		pricing_rule = make_pricing_rule(selling=1, discount_percentage=10)
		sales_order = make_sales_order(qty=2, do_not_submit=True)
		sales_order.items[0].update(
			{
				"price_list_rate": 100,
				"discount_percentage": 10,
				"rate": 90,
				"pricing_rules": json.dumps([pricing_rule.name]),
			}
		)
		sales_order.submit()
		self.assertEqual(flt(sales_order.grand_total), 180)

		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 2)])

		self.assertEqual(flt(proforma.items[0].rate), 90)
		self.assertEqual(flt(proforma.grand_total), 180)

	def test_amount_based_proforma(self):
		"""Amount basis: qty and amount are both entered; the rate is derived from them."""
		sales_order = make_sales_order(qty=10)  # rate 100
		so_detail = sales_order.items[0].name

		name = make_proforma_invoice(
			sales_order.name,
			json.dumps([{"so_detail": so_detail, "qty": 5, "amount": 250}]),
			based_on="Amount",
		)
		proforma = frappe.get_doc("Proforma Invoice", name)

		self.assertEqual(proforma.based_on, "Amount")
		item = proforma.items[0]
		self.assertEqual(flt(item.qty), 5)
		self.assertEqual(flt(item.rate), 50)  # 250 / 5
		self.assertEqual(flt(item.amount), 250)
		self.assertEqual(flt(proforma.grand_total), 250)

	def test_amount_basis_total_matches_line_amount(self):
		sales_order = make_sales_order(qty=10)
		name = make_proforma_invoice(
			sales_order.name,
			json.dumps([{"so_detail": sales_order.items[0].name, "qty": 3, "amount": 100}]),
			based_on="Amount",
		)

		self.assertEqual(flt(frappe.db.get_value("Proforma Invoice", name, "grand_total")), 100)

	def test_cancelled_proforma_keeps_pdf(self):
		"""Cancelling voids the proforma but keeps its PDF and status for the audit trail."""
		sales_order = make_sales_order(qty=10)
		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 4)])
		pdf = proforma.proforma_pdf
		self.assertTrue(pdf)

		proforma.cancel()
		proforma.reload()
		self.assertEqual(proforma.status, "Cancelled")
		self.assertEqual(proforma.proforma_pdf, pdf)

	def test_proformed_totals_exclude_cancelled(self):
		"""Cumulative issued proforma qty/amount per line, used by the dialog warning."""
		sales_order = make_sales_order(qty=10)  # rate 100
		so_detail = sales_order.items[0].name

		first = self.create_proforma(sales_order, [(so_detail, 4)])
		self.create_proforma(sales_order, [(so_detail, 3)])

		data = get_sales_order_items(sales_order.name)[0]
		self.assertEqual(flt(data["proformed_qty"]), 7)
		self.assertEqual(flt(data["proformed_amount"]), 700)

		first.cancel()
		data = get_sales_order_items(sales_order.name)[0]
		self.assertEqual(flt(data["proformed_qty"]), 3)
		self.assertEqual(flt(data["proformed_amount"]), 300)

	def test_hide_item_qty_only_applies_to_amount_basis(self):
		sales_order = make_sales_order(qty=10)
		so_detail = sales_order.items[0].name

		amount_based = make_proforma_invoice(
			sales_order.name,
			json.dumps([{"so_detail": so_detail, "qty": 5, "amount": 250}]),
			based_on="Amount",
			hide_item_qty=1,
		)
		self.assertEqual(frappe.db.get_value("Proforma Invoice", amount_based, "hide_item_qty"), 1)

		# ignored outside Amount basis
		qty_based = make_proforma_invoice(
			sales_order.name,
			json.dumps([{"so_detail": so_detail, "qty": 4}]),
			based_on="Quantity",
			hide_item_qty=1,
		)
		self.assertEqual(frappe.db.get_value("Proforma Invoice", qty_based, "hide_item_qty"), 0)

	def test_feature_toggle_is_enforced(self):
		sales_order = make_sales_order(qty=10)
		frappe.db.set_single_value("Selling Settings", "enable_proforma_invoice", 0)

		self.assertRaises(
			frappe.ValidationError,
			self.create_proforma,
			sales_order,
			[(sales_order.items[0].name, 4)],
		)

	def test_cannot_email_cancelled_proforma(self):
		sales_order = make_sales_order(qty=10)
		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 4)])
		proforma.cancel()

		self.assertRaises(frappe.ValidationError, send_proforma_email, proforma.name, "customer@example.com")

	def test_pdf_and_grand_total_are_set_by_the_server(self):
		sales_order = make_sales_order(qty=10)  # rate 100
		other_file = frappe.get_doc(
			{"doctype": "File", "file_name": "other.txt", "content": b"other", "is_private": 1}
		).insert()
		proforma = frappe.new_doc(
			"Proforma Invoice",
			sales_order=sales_order.name,
			proforma_pdf=other_file.file_url,
			grand_total=1,
			items=[{"so_detail": sales_order.items[0].name, "qty": 4}],
		)
		proforma.insert()
		proforma.submit()

		self.assertNotEqual(proforma.proforma_pdf, other_file.file_url)
		self.assertEqual(flt(proforma.grand_total), 400)

	def test_email_sends_only_the_proforma_attachment(self):
		sales_order = make_sales_order(qty=10)
		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 4)])
		other_file = frappe.get_doc(
			{"doctype": "File", "file_name": "other.txt", "content": b"other", "is_private": 1}
		).insert()
		proforma.db_set("proforma_pdf", other_file.file_url)

		self.assertRaises(frappe.ValidationError, send_proforma_email, proforma.name, "customer@example.com")

	def test_email_content_uses_template_from_selling_settings(self):
		template = make_email_template("Proforma {{ doc.name }}", "Advance payment for {{ doc.sales_order }}")
		frappe.db.set_single_value("Selling Settings", "proforma_email_template", template)
		proforma = frappe.get_doc(
			{"doctype": "Proforma Invoice", "name": "PRO-TEST-0001", "sales_order": "SO-TEST-0001"}
		)

		self.assertEqual(
			proforma.get_email_content(), ("Proforma PRO-TEST-0001", "Advance payment for SO-TEST-0001")
		)

	def test_email_content_without_template_is_default_text(self):
		frappe.db.set_single_value("Selling Settings", "proforma_email_template", None)
		proforma = frappe.get_doc({"doctype": "Proforma Invoice", "name": "PRO-TEST-0001"})

		self.assertEqual(
			proforma.get_email_content(),
			("Proforma Invoice PRO-TEST-0001", "Please find attached the proforma invoice PRO-TEST-0001."),
		)

	def test_line_description_is_editable(self):
		sales_order = make_sales_order(qty=10, do_not_submit=True)
		sales_order.items[0].description = "Ordered description"
		sales_order.submit()
		so_detail = sales_order.items[0].name

		edited = make_proforma_invoice(
			sales_order.name, json.dumps([{"so_detail": so_detail, "qty": 4, "description": "Edited"}])
		)
		unedited = self.create_proforma(sales_order, [(so_detail, 4)])

		self.assertEqual(get_sales_order_items(sales_order.name)[0]["description"], "Ordered description")
		self.assertEqual(frappe.get_doc("Proforma Invoice", edited).items[0].description, "Edited")
		self.assertEqual(unedited.items[0].description, "Ordered description")

	def test_update_items_cannot_delete_a_proformed_row(self):
		sales_order = make_sales_order(
			item_list=[
				{"item_code": "_Test Item", "qty": 5, "rate": 100},
				{"item_code": "_Test Item 2", "qty": 2, "rate": 50},
			]
		)
		proformed, other = sales_order.items
		proforma = self.create_proforma(sales_order, [(proformed.name, 2)])
		keep_other = json.dumps(
			[{"item_code": other.item_code, "qty": other.qty, "rate": other.rate, "docname": other.name}]
		)

		self.assertRaises(
			frappe.ValidationError, update_child_qty_rate, "Sales Order", keep_other, sales_order.name
		)

		proforma.cancel()
		update_child_qty_rate("Sales Order", keep_other, sales_order.name)
		sales_order.reload()
		self.assertEqual([item.name for item in sales_order.items], [other.name])

	def test_line_from_another_sales_order_is_rejected(self):
		sales_order = make_sales_order(qty=10)
		other_item = make_sales_order(qty=10).items[0]

		self.assertRaises(
			frappe.ValidationError,
			self.make_draft_proforma,
			sales_order,
			so_detail=other_item.name,
			item_code=other_item.item_code,
			qty=4,
		)

	def test_quantity_basis_bills_at_sales_order_rate(self):
		sales_order = make_sales_order(qty=10)
		so_item = sales_order.items[0]

		proforma = self.make_draft_proforma(
			sales_order, so_detail=so_item.name, item_code=so_item.item_code, qty=4, rate=1, amount=1
		)

		item = proforma.items[0]
		self.assertEqual(item.item_code, so_item.item_code)
		self.assertEqual(flt(item.rate), flt(so_item.rate))
		self.assertEqual(flt(item.amount), 4 * flt(so_item.rate))

	def test_amended_proforma_is_rejected(self):
		proforma = frappe.get_doc({"doctype": "Proforma Invoice", "amended_from": "PRO-TEST-0001"})

		self.assertRaises(frappe.ValidationError, proforma.validate_amended_doc)

	def test_requires_submitted_sales_order(self):
		"""The server rejects a proforma against a draft Sales Order (the button is JS-gated only)."""
		sales_order = make_sales_order(qty=10, do_not_submit=True)

		self.assertRaises(
			frappe.ValidationError,
			self.create_proforma,
			sales_order,
			[(sales_order.items[0].name, 4)],
		)
