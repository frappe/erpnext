# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import flt, get_link_to_form, getdate

from erpnext.accounts.party import CROSS_PARTY_FIELD_NO_MAP, _get_party_details


@frappe.whitelist()
def make_maintenance_schedule(source_name: str, target_doc: str | Document | None = None):
	doclist = get_mapped_doc(
		"Sales Invoice",
		source_name,
		{
			"Sales Invoice": {"doctype": "Maintenance Schedule", "validation": {"docstatus": ["=", 1]}},
			"Sales Invoice Item": {
				"doctype": "Maintenance Schedule Item",
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_delivery_note(source_name: str, target_doc: Document | None = None):
	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
		target_doc.stock_qty = target_doc.qty * flt(source_doc.conversion_factor)

		target_doc.base_amount = target_doc.qty * flt(source_doc.base_rate)
		target_doc.amount = target_doc.qty * flt(source_doc.rate)

	doclist = get_mapped_doc(
		"Sales Invoice",
		source_name,
		{
			"Sales Invoice": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
			"Sales Invoice Item": {
				"doctype": "Delivery Note Item",
				"field_map": {
					"name": "si_detail",
					"parent": "against_sales_invoice",
					"serial_no": "serial_no",
					"sales_order": "against_sales_order",
					"so_detail": "so_detail",
					"cost_center": "cost_center",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.delivered_by_supplier != 1
				and not doc.scio_detail
				and not doc.dn_detail
				and doc.qty - doc.delivered_qty > 0,
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {
				"doctype": "Sales Team",
				"field_map": {"incentives": "incentives"},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name: str, target_doc: Document | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Sales Invoice", source_name, target_doc)


def get_inter_company_details(doc, doctype):
	if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"]:
		parties = frappe.db.get_all(
			"Supplier",
			fields=["name"],
			filters={"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company},
		)
		company = frappe.get_cached_value("Customer", doc.customer, "represents_company")

		if not parties:
			frappe.throw(
				_("No Supplier found for Inter Company Transactions which represents company {0}").format(
					frappe.bold(doc.company)
				)
			)

		party = get_internal_party(parties, "Supplier", doc)
	else:
		parties = frappe.db.get_all(
			"Customer",
			fields=["name"],
			filters={"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company},
		)
		company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

		if not parties:
			frappe.throw(
				_("No Customer found for Inter Company Transactions which represents company {0}").format(
					frappe.bold(doc.company)
				)
			)

		party = get_internal_party(parties, "Customer", doc)

	return {"party": party, "company": company}


def get_internal_party(parties, link_doctype, doc):
	if len(parties) == 1:
		party = parties[0].name
	else:
		# If more than one Internal Supplier/Customer, get supplier/customer on basis of address
		if doc.get("company_address") or doc.get("shipping_address"):
			party = frappe.db.get_value(
				"Dynamic Link",
				{
					"parent": doc.get("company_address") or doc.get("shipping_address"),
					"parenttype": "Address",
					"link_doctype": link_doctype,
				},
				"link_name",
			)

			if not party:
				party = parties[0].name
		else:
			party = parties[0].name

	return party


def validate_inter_company_transaction(doc, doctype):
	details = get_inter_company_details(doc, doctype)
	price_list = (
		doc.selling_price_list
		if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"]
		else doc.buying_price_list
	)
	valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	if not valid_price_list and not doc.is_internal_transfer():
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))

	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

	company = details.get("company")
	default_currency = frappe.get_cached_value("Company", company, "default_currency")
	if default_currency != doc.currency:
		frappe.throw(
			_("Company currencies of both the companies should match for Inter Company Transactions.")
		)

	return


@frappe.whitelist()
def make_inter_company_purchase_invoice(source_name: str, target_doc: Document | None = None):
	return make_inter_company_transaction("Sales Invoice", source_name, target_doc)


def make_inter_company_transaction(doctype, source_name, target_doc=None):
	if doctype in ["Sales Invoice", "Sales Order"]:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
		target_detail_field = "sales_invoice_item" if doctype == "Sales Invoice" else "sales_order_item"
		source_document_warehouse_field = "target_warehouse"
		target_document_warehouse_field = "from_warehouse"
		received_items = get_received_items(source_name, target_doctype, target_detail_field)
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"
		source_document_warehouse_field = "from_warehouse"
		target_document_warehouse_field = "target_warehouse"
		received_items = {}

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

	def update_details(source_doc, target_doc, source_parent):
		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			_apply_purchase_party_details(target_doc, source_doc, details)
		else:
			_apply_sales_party_details(target_doc, source_doc, details)

	def update_item(source, target, source_parent):
		target.qty = flt(source.qty) - received_items.get(source.name, 0.0)
		if source.doctype == "Purchase Order Item" and target.doctype == "Sales Order Item":
			target.purchase_order = source.parent
			target.purchase_order_item = source.name
			target.material_request = source.material_request
			target.material_request_item = source.material_request_item

		if (
			source.get("purchase_order")
			and source.get("purchase_order_item")
			and target.doctype == "Purchase Invoice Item"
		):
			target.purchase_order = source.purchase_order
			target.po_detail = source.purchase_order_item

		if (source.get("serial_no") or source.get("batch_no")) and not source.get("serial_and_batch_bundle"):
			target.use_serial_batch_fields = 1

	item_field_map = {
		"doctype": target_doctype + " Item",
		"field_no_map": ["income_account", "expense_account", "cost_center", "warehouse"],
		"field_map": {
			"rate": "rate",
		},
		"postprocess": update_item,
		"condition": lambda doc: doc.qty - received_items.get(doc.name, 0.0) > 0,
	}

	if doctype in ["Sales Invoice", "Sales Order"]:
		item_field_map["field_map"].update(
			{
				"name": target_detail_field,
			}
		)

	if source_doc.get("update_stock"):
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: target_document_warehouse_field,
				"batch_no": "batch_no",
				"serial_no": "serial_no",
			}
		)
	elif target_doctype == "Sales Order":
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: "warehouse",
			}
		)

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": target_doctype,
				"postprocess": update_details,
				"set_target_warehouse": "set_from_warehouse",
				"field_no_map": [*CROSS_PARTY_FIELD_NO_MAP, "set_warehouse", "cost_center"],
			},
			doctype + " Item": item_field_map,
		},
		target_doc,
		set_missing_values,
	)
	if not doclist.get("items"):
		frappe.throw(
			_(
				"Cannot create Intercompany {0}. All items in the source {1} have already been fully invoiced. "
				"Please check the existing linked {2}s."
			).format(target_doctype, doctype, target_doctype)
		)

	return doclist


def _get_linked_address(address, link_doctype, link_name):
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


def _apply_purchase_party_details(target_doc, source_doc, details):
	currency = frappe.db.get_value("Supplier", details.get("party"), "default_currency")
	target_doc.company = details.get("company")
	target_doc.supplier = details.get("party")
	target_doc.is_internal_supplier = 1
	target_doc.ignore_pricing_rule = 1
	target_doc.buying_price_list = source_doc.selling_price_list

	# Invert Addresses
	if source_doc.company_address and _get_linked_address(
		source_doc.company_address, "Supplier", details.get("party")
	):
		update_address(target_doc, "supplier_address", "address_display", source_doc.company_address)
	if source_doc.dispatch_address_name and _get_linked_address(
		source_doc.dispatch_address_name, "Company", details.get("company")
	):
		update_address(
			target_doc, "dispatch_address", "dispatch_address_display", source_doc.dispatch_address_name
		)
	if source_doc.shipping_address_name and _get_linked_address(
		source_doc.shipping_address_name, "Company", details.get("company")
	):
		update_address(
			target_doc, "shipping_address", "shipping_address_display", source_doc.shipping_address_name
		)
	if source_doc.customer_address and _get_linked_address(
		source_doc.customer_address, "Company", details.get("company")
	):
		update_address(target_doc, "billing_address", "billing_address_display", source_doc.customer_address)

	if currency:
		target_doc.currency = currency

	update_taxes(
		target_doc,
		party=target_doc.supplier,
		party_type="Supplier",
		company=target_doc.company,
		doctype=target_doc.doctype,
		party_address=target_doc.supplier_address,
		company_address=target_doc.shipping_address,
	)


def _apply_sales_party_details(target_doc, source_doc, details):
	currency = frappe.db.get_value("Customer", details.get("party"), "default_currency")
	target_doc.company = details.get("company")
	target_doc.customer = details.get("party")
	target_doc.selling_price_list = source_doc.buying_price_list

	if source_doc.supplier_address and _get_linked_address(
		source_doc.supplier_address, "Company", details.get("company")
	):
		update_address(target_doc, "company_address", "company_address_display", source_doc.supplier_address)
	if source_doc.shipping_address and _get_linked_address(
		source_doc.shipping_address, "Customer", details.get("party")
	):
		update_address(target_doc, "shipping_address_name", "shipping_address", source_doc.shipping_address)
	if source_doc.shipping_address and _get_linked_address(
		source_doc.shipping_address, "Customer", details.get("party")
	):
		update_address(target_doc, "customer_address", "address_display", source_doc.shipping_address)

	if currency:
		target_doc.currency = currency

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


@frappe.whitelist()
def get_received_items(reference_name: str, doctype: str, reference_fieldname: str):
	reference_field = "inter_company_invoice_reference"
	if doctype == "Purchase Order":
		reference_field = "inter_company_order_reference"

	filters = {
		reference_field: reference_name,
		"docstatus": 1,
	}

	target_doctypes = frappe.get_all(
		doctype,
		filters=filters,
		pluck="name",
	)
	received_items_map = {}
	if target_doctypes:
		received_items_data = frappe.get_all(
			doctype + " Item",
			filters={"parent": ("in", target_doctypes)},
			fields=[reference_fieldname, "qty"],
		)
		for item in received_items_data:
			key = item.get(reference_fieldname)
			if key:
				received_items_map[key] = received_items_map.get(key, 0.0) + flt(item.qty)

	return received_items_map


def set_purchase_references(doc):
	# add internal PO or PR links if any

	if doc.is_internal_transfer():
		if doc.doctype == "Purchase Receipt":
			so_item_map = get_delivery_note_details(doc.inter_company_invoice_reference)

			if so_item_map:
				pd_item_map, parent_child_map, warehouse_map = get_pd_details(
					"Purchase Order Item", so_item_map, "sales_order_item"
				)

				update_pr_items(doc, so_item_map, pd_item_map, parent_child_map, warehouse_map)

		elif doc.doctype == "Purchase Invoice":
			dn_item_map, so_item_map = get_sales_invoice_details(doc.inter_company_invoice_reference)
			# First check for Purchase receipt
			if list(dn_item_map.values()):
				pd_item_map, parent_child_map, warehouse_map = get_pd_details(
					"Purchase Receipt Item", dn_item_map, "delivery_note_item"
				)

				update_pi_items(
					doc,
					"pr_detail",
					"purchase_receipt",
					dn_item_map,
					pd_item_map,
					parent_child_map,
					warehouse_map,
				)


def update_pi_items(
	doc,
	detail_field,
	parent_field,
	sales_item_map,
	purchase_item_map,
	parent_child_map,
	warehouse_map,
):
	for item in doc.get("items"):
		item.set(detail_field, purchase_item_map.get(sales_item_map.get(item.sales_invoice_item)))
		item.set(parent_field, parent_child_map.get(sales_item_map.get(item.sales_invoice_item)))
		if doc.update_stock:
			item.warehouse = warehouse_map.get(sales_item_map.get(item.sales_invoice_item))
			if not item.warehouse and item.get("purchase_order") and item.get("purchase_order_item"):
				item.warehouse = frappe.db.get_value(
					"Purchase Order Item", item.purchase_order_item, "warehouse"
				)


def update_pr_items(doc, sales_item_map, purchase_item_map, parent_child_map, warehouse_map):
	for item in doc.get("items"):
		item.warehouse = warehouse_map.get(sales_item_map.get(item.delivery_note_item))
		if not item.warehouse and item.get("purchase_order") and item.get("purchase_order_item"):
			item.warehouse = frappe.db.get_value("Purchase Order Item", item.purchase_order_item, "warehouse")


def get_delivery_note_details(internal_reference):
	si_item_details = frappe.get_all(
		"Delivery Note Item", fields=["name", "so_detail"], filters={"parent": internal_reference}
	)

	return {d.name: d.so_detail for d in si_item_details if d.so_detail}


def get_sales_invoice_details(internal_reference):
	dn_item_map = {}
	so_item_map = {}

	si_item_details = frappe.get_all(
		"Sales Invoice Item",
		fields=["name", "so_detail", "dn_detail"],
		filters={"parent": internal_reference},
	)

	for d in si_item_details:
		if d.dn_detail:
			dn_item_map.setdefault(d.name, d.dn_detail)
		if d.so_detail:
			so_item_map.setdefault(d.name, d.so_detail)

	return dn_item_map, so_item_map


def get_pd_details(doctype, sd_detail_map, sd_detail_field):
	pd_item_map = {}
	accepted_warehouse_map = {}
	parent_child_map = {}

	pd_item_details = frappe.get_all(
		doctype,
		fields=[sd_detail_field, "name", "warehouse", "parent"],
		filters={sd_detail_field: ("in", list(sd_detail_map.values()))},
	)

	for d in pd_item_details:
		pd_item_map.setdefault(d.get(sd_detail_field), d.name)
		parent_child_map.setdefault(d.get(sd_detail_field), d.parent)
		accepted_warehouse_map.setdefault(d.get(sd_detail_field), d.warehouse)

	return pd_item_map, parent_child_map, accepted_warehouse_map


def update_taxes(
	doc,
	party=None,
	party_type=None,
	company=None,
	doctype=None,
	party_address=None,
	company_address=None,
	shipping_address_name=None,
	master_doctype=None,
):
	# Update Party Details
	party_details = _get_party_details(
		party=party,
		party_type=party_type,
		company=company,
		doctype=doctype,
		party_address=party_address,
		company_address=company_address,
		shipping_address=shipping_address_name,
	)

	# Update taxes and charges if any
	doc.taxes_and_charges = party_details.get("taxes_and_charges")
	doc.set("taxes", party_details.get("taxes"))


def update_address(doc, address_field, address_display_field, address_name):
	doc.set(address_field, address_name)
	fetch_values = get_fetch_values(doc.doctype, address_field, address_name)

	for key, value in fetch_values.items():
		doc.set(key, value)

	doc.set(address_display_field, get_address_display(doc.get(address_field)))


@frappe.whitelist()
def create_invoice_discounting(source_name: str, target_doc: str | Document | None = None):
	invoice = frappe.get_doc("Sales Invoice", source_name)
	invoice_discounting = frappe.new_doc("Invoice Discounting")
	invoice_discounting.company = invoice.company
	invoice_discounting.append(
		"invoices",
		{
			"sales_invoice": source_name,
			"customer": invoice.customer,
			"posting_date": invoice.posting_date,
			"outstanding_amount": invoice.outstanding_amount,
		},
	)

	return invoice_discounting


@frappe.whitelist()
def create_dunning(
	source_name: str, target_doc: str | Document | None = None, ignore_permissions: bool = False
):
	def postprocess_dunning(source, target):
		from erpnext.accounts.doctype.dunning.dunning import get_dunning_letter_text

		dunning_type = frappe.db.exists("Dunning Type", {"is_default": 1, "company": source.company})
		if dunning_type:
			dunning_type = frappe.get_doc("Dunning Type", dunning_type)
			target.dunning_type = dunning_type.name
			target.rate_of_interest = dunning_type.rate_of_interest
			target.dunning_fee = dunning_type.dunning_fee
			target.income_account = dunning_type.income_account
			target.cost_center = dunning_type.cost_center
			letter_text = get_dunning_letter_text(
				dunning_type=dunning_type.name, doc=target.as_dict(), language=source.language
			)

			if letter_text:
				target.body_text = letter_text.get("body_text")
				target.closing_text = letter_text.get("closing_text")
				target.language = letter_text.get("language")

		# update outstanding from doc
		if source.payment_schedule and len(source.payment_schedule) == 1:
			for row in target.overdue_payments:
				if row.payment_schedule == source.payment_schedule[0].name:
					# outstanding_amount is in the party account currency, but the Overdue Payment
					# row is in the invoice's transaction currency. When they differ, use the
					# payment schedule's own outstanding — it is kept in transaction currency and
					# updated as payments are allocated, so it stays correct even when the invoice
					# and its payments post at different exchange rates (#56006).
					if source.party_account_currency and source.party_account_currency != source.currency:
						row.outstanding = source.payment_schedule[0].outstanding
					else:
						row.outstanding = source.get("outstanding_amount")

		target.validate()

	return get_mapped_doc(
		from_doctype="Sales Invoice",
		from_docname=source_name,
		target_doc=target_doc,
		table_maps={
			"Sales Invoice": {
				"doctype": "Dunning",
				"field_map": {"customer_address": "customer_address", "parent": "sales_invoice"},
			},
			"Payment Schedule": {
				"doctype": "Overdue Payment",
				"field_map": {"name": "payment_schedule", "parent": "sales_invoice"},
				"condition": lambda doc: doc.outstanding > 0 and getdate(doc.due_date) < getdate(),
			},
		},
		postprocess=postprocess_dunning,
		ignore_permissions=ignore_permissions,
	)
