# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Inter-company transaction helpers for Sales Invoice."""

import frappe
from frappe import _


def validate_inter_company_party(
	doctype: str, party: str, company: str, inter_company_reference: str | None
) -> None:
	if not party:
		return

	if doctype in ["Sales Invoice", "Sales Order"]:
		partytype, ref_partytype, internal = "Customer", "Supplier", "is_internal_customer"
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
	else:
		partytype, ref_partytype, internal = "Supplier", "Customer", "is_internal_supplier"
		ref_doc = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"

	if inter_company_reference:
		doc = frappe.get_doc(ref_doc, inter_company_reference)
		ref_party = doc.supplier if doctype in ["Sales Invoice", "Sales Order"] else doc.customer
		if frappe.db.get_value(partytype, {"represents_company": doc.company}, "name") != party:
			frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(_(partytype)))
		if frappe.get_cached_value(ref_partytype, ref_party, "represents_company") != company:
			frappe.throw(_("Invalid Company for Inter Company Transaction."))

	elif frappe.db.get_value(partytype, {"name": party, internal: 1}, "name") == party:
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


def update_linked_doc(doctype: str, name: str, inter_company_reference: str | None) -> None:
	ref_field = (
		"inter_company_invoice_reference"
		if doctype in ["Sales Invoice", "Purchase Invoice"]
		else "inter_company_order_reference"
	)
	if inter_company_reference:
		frappe.db.set_value(doctype, inter_company_reference, ref_field, name)


def unlink_inter_company_doc(doctype: str, name: str, inter_company_reference: str | None) -> None:
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Sales Invoice"
		ref_field = "inter_company_invoice_reference"
	else:
		ref_doc = "Purchase Order" if doctype == "Sales Order" else "Sales Order"
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, name, ref_field, "")
		frappe.db.set_value(ref_doc, inter_company_reference, ref_field, "")
