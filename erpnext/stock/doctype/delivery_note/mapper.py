# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.query_builder import DocType
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import flt

from erpnext.accounts.party import CROSS_PARTY_FIELD_NO_MAP, get_due_date
from erpnext.controllers.accounts_controller import get_taxes_and_charges, merge_taxes
from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle


def get_invoiced_qty_map(delivery_note: str) -> dict:
	"""returns a map: {dn_detail: invoiced_qty}"""
	sii = DocType("Sales Invoice Item")

	invoiced_qty_map = frappe._dict(
		(
			frappe.qb.from_(sii)
			.select(sii.dn_detail, Sum(sii.qty).as_("qty"))
			.where((sii.delivery_note == delivery_note) & (sii.docstatus == 1))
			.groupby(sii.dn_detail)
		).run()
	)

	return invoiced_qty_map


def get_returned_qty_map(delivery_note: str) -> dict:
	"""returns a map: {so_detail: returned_qty}"""
	dn = DocType("Delivery Note")
	dni = DocType("Delivery Note Item")

	returned_qty_map = frappe._dict(
		(
			frappe.qb.from_(dni)
			.join(dn)
			.on(dn.name == dni.parent)
			.select(dni.dn_detail, Sum(Abs(dni.qty)).as_("qty"))
			.where(
				(dn.docstatus == 1)
				& (dn.is_return == 1)
				& (dn.return_against == delivery_note)
				& (dni.qty <= 0)
			)
			.groupby(dni.dn_detail)
		).run()
	)

	return returned_qty_map


@frappe.whitelist()
def make_sales_invoice(
	source_name: str, target_doc: str | Document | None = None, args: dict | str | None = None
):
	from frappe.contacts.doctype.address.address import get_company_address

	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	doc = frappe.get_doc("Delivery Note", source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been Invoiced/Returned"))

		if args and args.get("merge_taxes"):
			merge_taxes(source, target)

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = to_make_invoice_qty_map[source_doc.name]
		target_doc._old_name = source_doc.name

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.name, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.name, 0))
			returned_qty_map[item_row.name] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doc = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Sales Invoice",
				"field_map": {"is_return": "is_return"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "dn_detail",
					"parent": "delivery_note",
					"so_detail": "so_detail",
					"against_sales_order": "sales_order",
					"cost_center": "cost_center",
				},
				"postprocess": update_item,
				"filter": lambda d: get_pending_qty(d) <= 0
				if not doc.get("is_return")
				else get_pending_qty(d) > 0,
				"condition": select_item,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"field_map": {"incentives": "incentives"},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	from frappe.utils import cint

	automatically_fetch_payment_terms = cint(
		frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)

	if not doc.is_return:
		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		ps = PaymentScheduleService(doc)
		so, doctype, fieldname = ps.get_order_details()
		if (
			ps.linked_order_has_payment_terms(so, fieldname, doctype)
			and not automatically_fetch_payment_terms
		):
			payment_terms_template = frappe.db.get_value(doctype, so, "payment_terms_template")
			doc.payment_terms_template = payment_terms_template
			doc.due_date = get_due_date(
				doc.posting_date,
				"Customer",
				doc.customer,
				doc.company,
				template_name=doc.payment_terms_template,
			)

		elif automatically_fetch_payment_terms:
			ps.set_payment_schedule()

	return doc


@frappe.whitelist()
def make_delivery_trip(
	source_name: str, target_doc: str | Document | None = None, kwargs: dict | None = None
):
	if not target_doc:
		target_doc = frappe.new_doc("Delivery Trip")

	def update_address(source_doc, target_doc, source_parent):
		target_doc.address = source_doc.shipping_address_name or source_doc.customer_address
		target_doc.customer_address = source_doc.shipping_address or source_doc.address_display

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Delivery Stop",
				"on_parent": target_doc,
				"field_map": {
					"name": "delivery_note",
					"contact_person": "contact",
					"contact_display": "customer_contact",
				},
				"postprocess": update_address,
			},
		},
		ignore_child_tables=True,
	)

	return doclist


@frappe.whitelist()
def make_installation_note(
	source_name: str, target_doc: str | Document | None = None, kwargs: dict | None = None
):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.installed_qty)
		target.serial_no = obj.serial_no

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {"doctype": "Installation Note", "validation": {"docstatus": ["=", 1]}},
			"Delivery Note Item": {
				"doctype": "Installation Note Item",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.installed_qty < doc.qty,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_packing_slip(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		target.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.packed_qty)

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Packing Slip",
				"field_map": {"name": "delivery_note", "letter_head": "letter_head"},
				"validation": {"docstatus": ["=", 0]},
			},
			"Delivery Note Item": {
				"doctype": "Packing Slip Item",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"batch_no": "batch_no",
					"description": "description",
					"qty": "qty",
					"uom": "stock_uom",
					"name": "dn_detail",
				},
				"postprocess": update_item,
				"condition": lambda item: (
					not is_product_bundle(item.item_code) and flt(item.packed_qty) < flt(item.qty)
				),
			},
			"Packed Item": {
				"doctype": "Packing Slip Item",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"batch_no": "batch_no",
					"description": "description",
					"qty": "qty",
					"name": "pi_detail",
				},
				"postprocess": update_item,
				"condition": lambda item: (flt(item.packed_qty) < flt(item.qty)),
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_shipment(source_name: str, target_doc: str | Document | None = None):
	def postprocess(source, target):
		user = frappe.db.get_value(
			"User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"], as_dict=1
		)
		target.pickup_contact_email = user.email
		pickup_contact_display = f"{user.full_name}"
		if user:
			if user.email:
				pickup_contact_display += "<br>" + user.email
			if user.phone:
				pickup_contact_display += "<br>" + user.phone
			if user.mobile_no and not user.phone:
				pickup_contact_display += "<br>" + user.mobile_no
		target.pickup_contact = pickup_contact_display

		# As we are using session user details in the pickup_contact then pickup_contact_person will be session user
		target.pickup_contact_person = frappe.session.user

		contact_person = source.contact_person or get_default_contact("Customer", source.customer)
		if contact_person:
			contact = frappe.db.get_value(
				"Contact", contact_person, ["email_id", "phone", "mobile_no"], as_dict=1
			)

			delivery_contact_display = source.contact_display or contact_person or ""
			if contact and not source.contact_display:
				if contact.email_id:
					delivery_contact_display += "<br>" + contact.email_id
				if contact.phone:
					delivery_contact_display += "<br>" + contact.phone
				if contact.mobile_no and not contact.phone:
					delivery_contact_display += "<br>" + contact.mobile_no

			target.delivery_contact_name = contact_person
			if contact and contact.email_id and not target.delivery_contact_email:
				target.delivery_contact_email = contact.email_id
			target.delivery_contact = delivery_contact_display

		if source.shipping_address_name:
			target.delivery_address_name = source.shipping_address_name
			target.delivery_address = source.shipping_address
		elif source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Shipment",
				"field_map": {
					"grand_total": "value_of_goods",
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
					"customer": "delivery_customer",
					"contact_person": "delivery_contact_name",
					"contact_email": "delivery_contact_email",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"base_amount": "grand_total",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name: str, target_doc: str | Document | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Delivery Note", source_name, target_doc)


@frappe.whitelist()
def make_inter_company_purchase_receipt(source_name: str, target_doc: str | Document | None = None):
	return make_inter_company_transaction("Delivery Note", source_name, target_doc)


def make_inter_company_transaction(doctype: str, source_name: str, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.mapper import (
		get_inter_company_details,
		set_purchase_references,
		update_address,
		update_taxes,
		validate_inter_company_transaction,
	)

	if doctype == "Delivery Note":
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Receipt"
		source_document_warehouse_field = "target_warehouse"
		target_document_warehouse_field = "from_warehouse"
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Delivery Note"
		source_document_warehouse_field = "from_warehouse"
		target_document_warehouse_field = "target_warehouse"

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

		if target.doctype == "Purchase Receipt":
			master_doctype = "Purchase Taxes and Charges Template"
		else:
			master_doctype = "Sales Taxes and Charges Template"

		if not target.get("taxes") and target.get("taxes_and_charges"):
			for tax in get_taxes_and_charges(master_doctype, target.get("taxes_and_charges")):
				target.append("taxes", tax)

		if not target.get("items"):
			frappe.throw(_("All items have already been received"))

	def update_details(source_doc, target_doc, source_parent):
		def _validate_address_link(address, link_doctype, link_name):
			return frappe.db.get_value(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": link_doctype,
					"link_name": link_name,
				},
				"parent",
			)

		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype == "Purchase Receipt":
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
			target_doc.is_internal_supplier = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			if source_doc.company_address and _validate_address_link(
				source_doc.company_address, "Supplier", details.get("party")
			):
				update_address(target_doc, "supplier_address", "address_display", source_doc.company_address)
			if source_doc.dispatch_address_name and _validate_address_link(
				source_doc.dispatch_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"dispatch_address",
					"dispatch_address_display",
					source_doc.dispatch_address_name,
				)
			if source_doc.shipping_address_name and _validate_address_link(
				source_doc.shipping_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"shipping_address",
					"shipping_address_display",
					source_doc.shipping_address_name,
				)
			if source_doc.customer_address and _validate_address_link(
				source_doc.customer_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "billing_address", "billing_address_display", source_doc.customer_address
				)

			update_taxes(
				target_doc,
				party=target_doc.supplier,
				party_type="Supplier",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address,
			)
		else:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.company_address = source_doc.supplier_address
			target_doc.selling_price_list = source_doc.buying_price_list
			target_doc.is_internal_customer = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			if source_doc.supplier_address and _validate_address_link(
				source_doc.supplier_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "company_address", "company_address_display", source_doc.supplier_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(
					target_doc, "shipping_address_name", "shipping_address", source_doc.shipping_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(target_doc, "customer_address", "address_display", source_doc.shipping_address)

			update_taxes(
				target_doc,
				party=target_doc.customer,
				party_type="Customer",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.customer_address,
				company_address=target_doc.company_address,
				shipping_address_name=target_doc.shipping_address_name,
			)

	def update_item(source, target, source_parent):
		if source_parent.doctype == "Delivery Note" and source.received_qty:
			target.qty = flt(source.qty) + flt(source.returned_qty) - flt(source.received_qty)

		if source.get("use_serial_batch_fields"):
			target.set("use_serial_batch_fields", 1)

		if (source.get("serial_no") or source.get("batch_no")) and not source.get("serial_and_batch_bundle"):
			target.set("use_serial_batch_fields", 1)

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": target_doctype,
				"postprocess": update_details,
				"field_no_map": [*CROSS_PARTY_FIELD_NO_MAP, "set_warehouse"],
			},
			doctype + " Item": {
				"doctype": target_doctype + " Item",
				"field_map": {
					source_document_warehouse_field: target_document_warehouse_field,
					"name": "delivery_note_item",
					"purchase_order": "purchase_order",
					"purchase_order_item": "purchase_order_item",
					"material_request": "material_request",
					"Material_request_item": "material_request_item",
				},
				"field_no_map": ["warehouse"],
				"condition": lambda item: item.received_qty < item.qty + item.returned_qty,
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist
