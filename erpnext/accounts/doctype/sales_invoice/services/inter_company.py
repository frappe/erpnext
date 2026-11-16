# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Inter-company transaction helpers for Sales Invoice."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

ORDER_ROW_LINKS = {
	"Sales Order": ("purchase_order_item", "Purchase Order Item"),
	"Purchase Order": ("sales_order_item", "Sales Order Item"),
}


def validate_inter_company_party(
	doctype: str, party: str, company: str, inter_company_reference: str | None
) -> None:
	if not party:
		return

	config = _get_inter_company_party_config(doctype)

	if inter_company_reference:
		_validate_against_reference(config, party, company, inter_company_reference)
	elif frappe.db.get_value(config.partytype, {"name": party, config.internal: 1}, "name") == party:
		_validate_internal_party_company(config.partytype, party, company)


def _get_inter_company_party_config(doctype: str) -> "frappe._dict":
	if doctype in ["Sales Invoice", "Sales Order"]:
		return frappe._dict(
			partytype="Customer",
			ref_partytype="Supplier",
			internal="is_internal_customer",
			ref_doc="Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order",
		)
	return frappe._dict(
		partytype="Supplier",
		ref_partytype="Customer",
		internal="is_internal_supplier",
		ref_doc="Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order",
	)


def _validate_against_reference(config, party: str, company: str, inter_company_reference: str) -> None:
	doc = frappe.get_doc(config.ref_doc, inter_company_reference)
	ref_party = doc.supplier if config.partytype == "Customer" else doc.customer
	if (
		frappe.db.get_value(config.partytype, {"represents_company": doc.company, "disabled": 0}, "name")
		!= party
	):
		frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(_(config.partytype)))
	if frappe.get_cached_value(config.ref_partytype, ref_party, "represents_company") != company:
		frappe.throw(_("Invalid Company for Inter Company Transaction."))


def _validate_internal_party_company(partytype: str, party: str, company: str) -> None:
	companies = [
		d.company
		for d in frappe.get_all(
			"Allowed To Transact With",
			fields=["company"],
			filters={"parenttype": partytype, "parent": party},
		)
	]
	if company not in companies:
		frappe.throw(
			_(
				"{0} not allowed to transact with {1}. Please change the Company or add the Company in the 'Allowed To Transact With'-Section in the Customer record."
			).format(_(partytype), company)
		)


def get_inter_company_counterpart(doctype: str) -> tuple[str, str]:
	"""Return the counterpart doctype and the field both documents use to reference each other."""
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Sales Invoice"
		return ref_doc, "inter_company_invoice_reference"

	ref_doc = "Purchase Order" if doctype == "Sales Order" else "Sales Order"
	return ref_doc, "inter_company_order_reference"


def update_linked_doc(doctype: str, name: str, inter_company_reference: str | None) -> None:
	ref_doc, ref_field = get_inter_company_counterpart(doctype)
	if inter_company_reference:
		frappe.db.set_value(ref_doc, inter_company_reference, ref_field, name)


def validate_counterpart_is_free(doc) -> None:
	"""Drafts are mapped from submitted documents only, so check again on submit."""
	if doc.get("is_return"):
		return

	if doc.doctype == "Sales Invoice":
		validate_purchase_invoice_is_free(doc)
	elif doc.doctype in ORDER_ROW_LINKS:
		validate_inter_company_order_qty(doc)


def validate_purchase_invoice_is_free(doc) -> None:
	"""Purchase Invoice rows link no Sales Invoice rows, so it can have only one Sales Invoice."""
	purchase_invoice = doc.inter_company_invoice_reference
	if not purchase_invoice:
		return

	sales_invoice = frappe.db.get_value(
		"Purchase Invoice", purchase_invoice, "inter_company_invoice_reference"
	)
	if (
		sales_invoice
		and sales_invoice != doc.name
		and frappe.db.get_value("Sales Invoice", sales_invoice, "docstatus") == 1
	):
		frappe.throw(
			_("Purchase Invoice {0} already has Sales Invoice {1}.").format(
				purchase_invoice, get_link_to_form("Sales Invoice", sales_invoice)
			)
		)


def validate_inter_company_order_qty(doc) -> None:
	source = doc.inter_company_order_reference
	if not source:
		return

	row_field, source_item_doctype = ORDER_ROW_LINKS[doc.doctype]
	source_qty = dict(
		frappe.get_all(source_item_doctype, {"parent": source}, ["name", "stock_qty"], as_list=True)
	)
	ordered_qty = get_inter_company_ordered_qty(doc, row_field)

	for row in doc.items:
		source_row = row.get(row_field)
		if source_row not in source_qty:
			continue

		ordered_qty[source_row] += flt(row.stock_qty)
		precision = row.precision("stock_qty")
		if flt(ordered_qty[source_row], precision) > flt(source_qty[source_row], precision):
			source_doctype = source_item_doctype.removesuffix(" Item")
			frappe.throw(
				_("Row #{0}: Item {1} is already ordered in full against {2} {3}.").format(
					row.idx,
					frappe.bold(row.item_code),
					source_doctype,
					get_link_to_form(source_doctype, source),
				)
			)


def get_inter_company_ordered_qty(doc, row_field: str) -> defaultdict:
	"""Stock qty of the other submitted orders against the same counterpart, by counterpart row."""
	other_orders = frappe.get_all(
		doc.doctype,
		filters={
			"inter_company_order_reference": doc.inter_company_order_reference,
			"docstatus": 1,
			"name": ("!=", doc.name),
		},
		pluck="name",
	)
	ordered_qty = defaultdict(float)
	if not other_orders:
		return ordered_qty

	for row in frappe.get_all(
		doc.doctype + " Item", {"parent": ("in", other_orders)}, [row_field, "stock_qty"]
	):
		ordered_qty[row.get(row_field)] += flt(row.stock_qty)

	return ordered_qty


def unlink_inter_company_doc(doctype: str, name: str, inter_company_reference: str | None) -> None:
	ref_doc, ref_field = get_inter_company_counterpart(doctype)
	if not inter_company_reference:
		return

	frappe.db.set_value(doctype, name, ref_field, "")
	if frappe.db.get_value(ref_doc, inter_company_reference, ref_field) != name:
		return

	remaining_counterpart = frappe.db.get_value(doctype, {ref_field: inter_company_reference, "docstatus": 1})
	frappe.db.set_value(ref_doc, inter_company_reference, ref_field, remaining_counterpart or "")
