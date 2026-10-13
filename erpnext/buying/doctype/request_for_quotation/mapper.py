# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.accounts.party import _get_party_details, get_party_account_currency
from erpnext.stock.doctype.material_request.mapper import set_missing_values


@frappe.whitelist()
def make_supplier_quotation_from_rfq(
	source_name: str, target_doc: str | dict | Document | None = None, for_supplier: str | None = None
):
	def postprocess(source, target_doc):
		if for_supplier:
			target_doc.supplier = for_supplier
			args = _get_party_details(for_supplier, party_type="Supplier", ignore_permissions=True)
			target_doc.currency = args.currency or get_party_account_currency(
				"Supplier", for_supplier, source.company
			)
			target_doc.buying_price_list = args.buying_price_list or frappe.db.get_single_value(
				"Buying Settings", "buying_price_list"
			)
		set_missing_values(source, target_doc)

	doclist = get_mapped_doc(
		"Request for Quotation",
		source_name,
		{
			"Request for Quotation": {
				"doctype": "Supplier Quotation",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {"opportunity": "opportunity"},
			},
			"Request for Quotation Item": {
				"doctype": "Supplier Quotation Item",
				"field_map": {
					"name": "request_for_quotation_item",
					"parent": "request_for_quotation",
					"project_name": "project",
					"cost_center": "cost_center",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


# This method is used to make supplier quotation from supplier's portal.
@frappe.whitelist(methods=["POST"])
def create_supplier_quotation(doc: str | Document | dict):
	doc = frappe.parse_json(doc)
	supplier = doc.get("supplier")

	if frappe.session.user not in frappe.get_all(
		"Portal User", {"parenttype": "Supplier", "parent": supplier}, pluck="user"
	):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	rfq = get_quotable_rfq(doc.get("name"), supplier)
	validate_existing_supplier_quotation(supplier, rfq.name)

	sq_doc = frappe.get_doc(
		{
			"doctype": "Supplier Quotation",
			"supplier": supplier,
			"terms": doc.get("terms"),
			"company": rfq.company,
			"currency": doc.get("currency") or get_party_account_currency("Supplier", supplier, rfq.company),
			"buying_price_list": doc.get("buying_price_list")
			or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
		}
	)
	add_items(sq_doc, supplier, rfq, doc.get("items"))
	sq_doc.flags.ignore_permissions = True
	sq_doc.run_method("set_missing_values")
	sq_doc.save()
	frappe.msgprint(_("Supplier Quotation {0} Created").format(sq_doc.name))
	return sq_doc.name


def get_quotable_rfq(rfq_name, supplier):
	"""Return the submitted Request for Quotation `supplier` was invited to quote on."""
	rfq = frappe.get_doc("Request for Quotation", rfq_name)
	if rfq.docstatus != 1 or supplier not in {row.supplier for row in rfq.suppliers}:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return rfq


def validate_existing_supplier_quotation(supplier, request_for_quotation):
	rfq = frappe.qb.DocType("Request for Quotation")
	(frappe.qb.from_(rfq).select(rfq.name).where(rfq.name == request_for_quotation).for_update()).run()

	sq = frappe.qb.DocType("Supplier Quotation")
	sqi = frappe.qb.DocType("Supplier Quotation Item")
	existing_quotation = (
		frappe.qb.from_(sq)
		.inner_join(sqi)
		.on(sq.name == sqi.parent)
		.select(sq.name)
		.where(
			(sq.docstatus < 2)
			& (sq.supplier == supplier)
			& (sqi.request_for_quotation == request_for_quotation)
		)
		.limit(1)
	).run(as_dict=True)

	if existing_quotation:
		frappe.throw(
			_("Supplier Quotation {0} already exists against Request for Quotation {1}").format(
				frappe.bold(existing_quotation[0].name),
				frappe.bold(request_for_quotation),
			)
		)


def add_items(sq_doc, supplier, rfq, items):
	rfq_rows = {row.name: row for row in rfq.items}
	for data in items:
		if isinstance(data, dict):
			data = frappe._dict(data)

		if data.name not in rfq_rows:
			frappe.throw(_("Row {0} is not part of Request for Quotation {1}.").format(data.idx, rfq.name))

		create_rfq_items(sq_doc, supplier, rfq_rows[data.name], data)


def create_rfq_items(sq_doc, supplier, rfq_row, data):
	"""Take the item and its UOM from the RFQ row; only the qty and rate come from the supplier."""
	args = {
		field: rfq_row.get(field)
		for field in [
			"item_code",
			"item_name",
			"description",
			"conversion_factor",
			"warehouse",
			"material_request",
			"material_request_item",
			"uom",
			"cost_center",
		]
	}
	args.update(
		{
			"qty": flt(data.get("qty")),
			"rate": flt(data.get("rate")),
			"request_for_quotation_item": rfq_row.name,
			"request_for_quotation": rfq_row.parent,
			"supplier_part_no": frappe.db.get_value(
				"Item Supplier", {"parent": rfq_row.item_code, "supplier": supplier}, "supplier_part_no"
			),
		}
	)

	sq_doc.append("items", args)


@frappe.whitelist()
def get_item_from_material_requests_based_on_supplier(
	source_name: str, target_doc: str | dict | Document | None = None
):
	Item = frappe.qb.DocType("Item")
	Item_Supp = frappe.qb.DocType("Item Supplier")
	MR = frappe.qb.DocType("Material Request")
	MR_Item = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(MR_Item)
		.join(MR)
		.on(MR_Item.parent == MR.name)
		.join(Item)
		.on(MR_Item.item_code == Item.name)
		.join(Item_Supp)
		.on(Item.name == Item_Supp.parent)
		.select(MR.name, MR_Item.item_code)
		.where(Item_Supp.supplier == source_name)
		.where(MR.status != "Stopped")
		.where(MR.material_request_type == "Purchase")
		.where(MR.docstatus == 1)
		.where(MR.per_ordered < 99.99)
	)

	mr_items_list = query.run(as_dict=True)

	material_requests = {}
	for d in mr_items_list:
		material_requests.setdefault(d.name, []).append(d.item_code)

	for mr, items in material_requests.items():
		target_doc = get_mapped_doc(
			"Material Request",
			mr,
			{
				"Material Request": {
					"doctype": "Request for Quotation",
					"validation": {
						"docstatus": ["=", 1],
						"material_request_type": ["=", "Purchase"],
					},
				},
				"Material Request Item": {
					"doctype": "Request for Quotation Item",
					"condition": lambda row: row.item_code in items,
					"field_map": [
						["name", "material_request_item"],
						["parent", "material_request"],
						["uom", "uom"],
						["cost_center", "cost_center"],
					],
				},
			},
			target_doc,
		)

	return target_doc
