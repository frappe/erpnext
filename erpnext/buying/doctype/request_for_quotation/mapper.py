# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from erpnext.accounts.party import _get_party_details, get_party_account_currency
from erpnext.stock.doctype.material_request.mapper import set_missing_values


@frappe.whitelist()
def make_supplier_quotation_from_rfq(
	source_name: str, target_doc: str | Document | None = None, for_supplier: str | None = None
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
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


# This method is used to make supplier quotation from supplier's portal.
@frappe.whitelist()
def create_supplier_quotation(doc: str | Document | dict):
	if isinstance(doc, str):
		doc = json.loads(doc)

	if frappe.session.user not in frappe.get_all(
		"Portal User", {"parent": doc.get("supplier")}, pluck="user"
	):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	try:
		sq_doc = frappe.get_doc(
			{
				"doctype": "Supplier Quotation",
				"supplier": doc.get("supplier"),
				"terms": doc.get("terms"),
				"company": doc.get("company"),
				"currency": doc.get("currency")
				or get_party_account_currency("Supplier", doc.get("supplier"), doc.get("company")),
				"buying_price_list": doc.get("buying_price_list")
				or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
			}
		)
		add_items(sq_doc, doc.get("supplier"), doc.get("items"))
		sq_doc.flags.ignore_permissions = True
		sq_doc.run_method("set_missing_values")
		sq_doc.save()
		frappe.msgprint(_("Supplier Quotation {0} Created").format(sq_doc.name))
		return sq_doc.name
	except Exception:
		return None


def add_items(sq_doc, supplier, items):
	for data in items:
		if isinstance(data, dict):
			data = frappe._dict(data)

		create_rfq_items(sq_doc, supplier, data)


def create_rfq_items(sq_doc, supplier, data):
	args = {}

	for field in [
		"item_code",
		"item_name",
		"description",
		"qty",
		"rate",
		"conversion_factor",
		"warehouse",
		"material_request",
		"material_request_item",
		"stock_qty",
		"uom",
	]:
		args[field] = data.get(field)

	args.update(
		{
			"request_for_quotation_item": data.name,
			"request_for_quotation": data.parent,
			"supplier_part_no": frappe.db.get_value(
				"Item Supplier", {"parent": data.item_code, "supplier": supplier}, "supplier_part_no"
			),
		}
	)

	sq_doc.append("items", args)


@frappe.whitelist()
def get_item_from_material_requests_based_on_supplier(
	source_name: str, target_doc: str | Document | None = None
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
					],
				},
			},
			target_doc,
		)

	return target_doc
