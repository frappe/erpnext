# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import flt

from erpnext.controllers.accounts_controller import merge_taxes
from erpnext.stock.doctype.delivery_note.mapper import make_inter_company_transaction
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	get_batches_from_bundle,
	get_serial_nos_from_bundle,
)


def get_invoiced_qty_map(purchase_receipt: str) -> dict:
	"""returns a map: {pr_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for pr_detail, qty in frappe.db.sql(
		"""select pr_detail, qty from `tabPurchase Invoice Item`
		where purchase_receipt=%s and docstatus=1""",
		purchase_receipt,
	):
		if not invoiced_qty_map.get(pr_detail):
			invoiced_qty_map[pr_detail] = 0
		invoiced_qty_map[pr_detail] += qty

	return invoiced_qty_map


def get_returned_qty_map(purchase_receipt: str) -> dict:
	"""returns a map: {pr_detail: returned_qty}"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.inner_join(pr_item)
		.on(pr.name == pr_item.parent)
		.select(pr_item.purchase_receipt_item, Sum(Abs(pr_item.qty)).as_("qty"))
		.where(
			(pr.docstatus == 1)
			& (pr.is_return == 1)
			& (pr.return_against == purchase_receipt)
			& (pr_item.purchase_receipt_item.isnotnull())
		)
		.groupby(pr_item.purchase_receipt_item)
	).run(as_list=1)

	return frappe._dict(query) if query else frappe._dict()


@frappe.whitelist()
def make_purchase_invoice(
	source_name: str | None, target_doc: str | Document | None = None, args: dict | str | None = None
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	from erpnext.accounts.party import get_payment_terms_template

	doc = frappe.get_doc("Purchase Receipt", source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been Invoiced/Returned"))

		doc = frappe.get_doc(target)
		doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
		doc.run_method("onload")
		doc.run_method("set_missing_values")

		if args and args.get("merge_taxes"):
			merge_taxes(source, doc)

		doc.run_method("calculate_taxes_and_totals")
		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		PaymentScheduleService(doc).set_payment_schedule()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty, returned_qty = get_pending_qty(source_doc)
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			target_doc.rejected_qty = 0
		target_doc.stock_qty = flt(target_doc.qty) * flt(
			target_doc.conversion_factor, target_doc.precision("conversion_factor")
		)
		returned_qty_map[source_doc.name] = returned_qty
		target_doc._old_name = source_doc.name

	def get_pending_qty(item_row):
		qty = item_row.qty
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			qty = item_row.received_qty

		pending_qty = qty - invoiced_qty_map.get(item_row.name, 0)

		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			return pending_qty, 0

		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
		if item_row.rejected_qty and returned_qty:
			returned_qty -= item_row.rejected_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		return pending_qty, returned_qty

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doclist = get_mapped_doc(
		"Purchase Receipt",
		source_name,
		{
			"Purchase Receipt": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"supplier_warehouse": "supplier_warehouse",
					"is_return": "is_return",
					"bill_date": "bill_date",
				},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Receipt Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"name": "pr_detail",
					"parent": "purchase_receipt",
					"qty": "received_qty",
					"purchase_order_item": "po_detail",
					"purchase_order": "purchase_order",
					"is_fixed_asset": "is_fixed_asset",
					"asset_location": "asset_location",
					"asset_category": "asset_category",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"filter": lambda d: (
					get_pending_qty(d)[0] <= 0 if not doc.get("is_return") else get_pending_qty(d)[0] > 0
				),
				"condition": select_item,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_purchase_return_against_rejected_warehouse(source_name: str):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Receipt", source_name, return_against_rejected_qty=True)


@frappe.whitelist()
def make_purchase_return(source_name: str, target_doc: str | Document | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Receipt", source_name, target_doc)


@frappe.whitelist()
def make_stock_entry(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Material Transfer"
		target.purpose = "Material Transfer"
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		if source_doc.serial_and_batch_bundle:
			serial_nos = get_serial_nos_from_bundle(source_doc.serial_and_batch_bundle)
			if serial_nos:
				serial_nos = "\n".join(serial_nos)

			batches = get_batches_from_bundle(source_doc.serial_and_batch_bundle)
			if batches:
				if len(batches) == 1:
					target_doc.use_serial_batch_fields = 1
					target_doc.batch_no = next(iter(batches))
				elif not serial_nos:
					cls_obj = SerialBatchCreation(
						{
							"type_of_transaction": "Outward",
							"serial_and_batch_bundle": source_doc.serial_and_batch_bundle,
							"item_code": source_doc.item_code,
							"warehouse": source_doc.warehouse,
						}
					)

					cls_obj.duplicate_package()

					target_doc.serial_and_batch_bundle = cls_obj.serial_and_batch_bundle

			if serial_nos:
				target_doc.use_serial_batch_fields = 1
				target_doc.serial_no = serial_nos

	doclist = get_mapped_doc(
		"Purchase Receipt",
		source_name,
		{
			"Purchase Receipt": {
				"doctype": "Stock Entry",
			},
			"Purchase Receipt Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"warehouse": "s_warehouse",
					"parent": "reference_purchase_receipt",
					"batch_no": "batch_no",
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_inter_company_delivery_note(source_name: str, target_doc: str | Document | None = None):
	return make_inter_company_transaction("Purchase Receipt", source_name, target_doc)
