# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, get_link_to_form

from erpnext.accounts.party import get_party_account
from erpnext.controllers.status_updater import get_allowance_for
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults


def set_missing_values(source, target):
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	target.run_method("set_use_serial_batch_fields")


@frappe.whitelist()
def make_purchase_receipt(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	has_unit_price_items = frappe.db.get_value("Purchase Order", source_name, "has_unit_price_items")

	def is_unit_price_row(source):
		return has_unit_price_items and source.qty == 0

	def get_max_receivable_qty(source):
		tolerance = flt(get_allowance_for(source.item_code, qty_or_amount="qty")[0])
		return flt(source.qty) * (100 + tolerance) / 100

	def update_item(obj, target, source_parent):
		received_qty = flt(obj.received_qty)
		qty = flt(obj.qty)
		pending_qty = qty - received_qty

		if is_unit_price_row(obj):
			target.qty = qty
		elif pending_qty > 0:
			target.qty = pending_qty
		else:
			target.qty = max(get_max_receivable_qty(obj) - received_qty, 0)

		target.stock_qty = target.qty * flt(obj.conversion_factor)
		target.amount = target.qty * flt(obj.rate)
		target.base_amount = target.qty * flt(obj.rate) * flt(source_parent.conversion_rate)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Purchase Receipt",
				"field_map": {"supplier_warehouse": "supplier_warehouse"},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_order_item",
					"parent": "purchase_order",
					"bom": "bom",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
					"sales_order": "sales_order",
					"sales_order_item": "sales_order_item",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"condition": lambda doc: (
					True
					if is_unit_price_row(doc)
					else abs(doc.received_qty) < abs(get_max_receivable_qty(doc))
				)
				and doc.delivered_by_supplier != 1
				and select_item(doc),
			},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "reset_value": True},
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def make_purchase_invoice(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	return get_mapped_purchase_invoice(source_name, target_doc, args=args)


@frappe.whitelist()
def make_purchase_invoice_from_portal(purchase_order_name: str):
	doc = get_mapped_purchase_invoice(purchase_order_name, ignore_permissions=True)
	if frappe.session.user not in frappe.get_all("Portal User", {"parent": doc.supplier}, pluck="user"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)
	doc.save()
	if not frappe.in_test:
		frappe.db.commit()  # nosemgrep
	frappe.response["type"] = "redirect"
	frappe.response.location = "/purchase-invoices/" + doc.name


def get_mapped_purchase_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)

		# Get the advance paid Journal Entries in Purchase Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		PaymentScheduleService(target).set_payment_schedule()
		target.credit_to = get_party_account("Supplier", source.supplier, source.company)

	def get_billed_qty(po_item_name):
		from frappe.query_builder.functions import Sum

		table = frappe.qb.DocType("Purchase Invoice Item")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.qty).as_("qty"))
			.where((table.docstatus == 1) & (table.po_detail == po_item_name))
		)
		return query.run(pluck="qty")[0] or 0

	def update_item(obj, target, source_parent):
		billed_qty = flt(get_billed_qty(obj.name))
		target.qty = flt(obj.qty) - billed_qty

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)
		target.cost_center = (
			obj.cost_center
			or frappe.db.get_value("Project", obj.project, "cost_center")
			or item.get("buying_cost_center")
			or item_group.get("buying_cost_center")
		)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	fields = {
		"Purchase Order": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"supplier_warehouse": "supplier_warehouse",
			},
			"field_no_map": ["payment_terms_template"],
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "po_detail",
				"parent": "purchase_order",
				"material_request": "material_request",
				"material_request_item": "material_request_item",
				"wip_composite_asset": "wip_composite_asset",
			},
			"postprocess": update_item,
			"condition": lambda doc: (
				doc.base_amount == 0
				or abs(doc.billed_amt) < abs(doc.amount)
				or doc.qty > flt(get_billed_qty(doc.name))
			)
			and select_item(doc),
		},
		"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "reset_value": True},
	}

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		fields,
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	return doc


@frappe.whitelist()
def make_inter_company_sales_order(source_name: str, target_doc: str | Document | None = None):
	from erpnext.accounts.doctype.sales_invoice.mapper import make_inter_company_transaction

	return make_inter_company_transaction("Purchase Order", source_name, target_doc)


@frappe.whitelist()
def make_subcontracting_order(
	source_name: str,
	target_doc: str | Document | None = None,
	save: bool = False,
	submit: bool = False,
	notify: bool = False,
):
	if not is_po_fully_subcontracted(source_name):
		target_doc = get_mapped_subcontracting_order(source_name, target_doc)

		if (save or submit) and frappe.has_permission(target_doc.doctype, "create"):
			target_doc.save()

			if submit and frappe.has_permission(target_doc.doctype, "submit", target_doc):
				try:
					target_doc.submit()
				except Exception as e:
					target_doc.add_comment("Comment", _("Submit Action Failed") + "<br><br>" + str(e))

			if notify:
				frappe.msgprint(
					_("Subcontracting Order {0} created.").format(
						get_link_to_form(target_doc.doctype, target_doc.name)
					),
					indicator="green",
					alert=True,
				)

		return target_doc
	else:
		frappe.throw(_("This Purchase Order has been fully subcontracted."))


def is_po_fully_subcontracted(po_name: str) -> bool:
	table = frappe.qb.DocType("Purchase Order Item")
	query = (
		frappe.qb.from_(table)
		.select(table.name)
		.where((table.parent == po_name) & (table.qty != table.subcontracted_qty))
	)
	return not query.run(as_dict=True)


def get_mapped_subcontracting_order(source_name: str, target_doc: str | Document | None = None) -> Document:
	def post_process(source_doc, target_doc):
		target_doc.populate_items_table()

		if target_doc.set_warehouse:
			for item in target_doc.items:
				item.warehouse = target_doc.set_warehouse
		else:
			if source_doc.set_warehouse:
				for item in target_doc.items:
					item.warehouse = source_doc.set_warehouse
			else:
				for idx, item in enumerate(target_doc.items):
					item.warehouse = source_doc.items[idx].warehouse

		for idx, item in enumerate(target_doc.items):
			item.job_card = source_doc.items[idx].job_card
			if not target_doc.supplier_warehouse:
				# WIP warehouse is set as Supplier Warehouse in Job Card
				target_doc.supplier_warehouse = frappe.get_cached_value(
					"Job Card", item.job_card, "wip_warehouse"
				)

		production_plan = set([item.production_plan for item in source_doc.items if item.production_plan])
		if production_plan:
			target_doc.production_plan = production_plan.pop()
		target_doc.reserve_stock = frappe.get_single_value(
			"Stock Settings", "auto_reserve_stock"
		) or frappe.get_value("Production Plan", target_doc.production_plan, "reserve_stock")

	if target_doc and isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
		for key in ["service_items", "items", "supplied_items"]:
			if key in target_doc:
				del target_doc[key]
		target_doc = json.dumps(target_doc)

	target_doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Subcontracting Order",
				"field_map": {},
				"field_no_map": ["total_qty", "total", "net_total"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Subcontracting Order Service Item",
				"field_map": {
					"name": "purchase_order_item",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
				},
				"field_no_map": ["qty", "fg_item_qty", "amount"],
				"condition": lambda item: item.qty != item.subcontracted_qty,
			},
		},
		target_doc,
		post_process,
	)

	return target_doc
