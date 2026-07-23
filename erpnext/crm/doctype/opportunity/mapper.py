# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.email.inbox import link_communication_to_document
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from erpnext.setup.utils import get_exchange_rate


@frappe.whitelist()
def make_quotation(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		quotation = frappe.get_doc(target)

		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")

		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)

		quotation.conversion_rate = exchange_rate

		# get default taxes
		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=quotation.company)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		if not source.get("items", []):
			quotation.opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"uom": "stock_uom",
				},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name: str, target_doc: str | Document | None = None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1.0

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [["name", "opportunity_item"], ["parent", "opportunity"], ["uom", "uom"]],
				"postprocess": update_item,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_customer(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		target.opportunity_name = source.name

		if source.opportunity_from == "Lead":
			target.lead_name = source.party_name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Customer",
				"field_map": {"currency": "default_currency", "customer_name": "customer_name"},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_supplier_quotation(source_name: str, target_doc: str | Document | None = None):
	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Supplier Quotation", "field_map": {"name": "opportunity"}},
			"Opportunity Item": {"doctype": "Supplier Quotation Item", "field_map": {"uom": "stock_uom"}},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist(methods=["POST"])
def make_opportunity_from_communication(
	communication: str, company: str, ignore_communication_links: bool = False
):
	from erpnext.crm.doctype.lead.mapper import make_lead_from_communication

	doc = frappe.get_doc("Communication", communication)

	lead = doc.reference_name if doc.reference_doctype == "Lead" else None
	if not lead:
		lead = make_lead_from_communication(communication, ignore_communication_links=True)

	opportunity_from = "Lead"

	opportunity = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"company": company,
			"opportunity_from": opportunity_from,
			"party_name": lead,
		}
	).insert()

	link_communication_to_document(doc, "Opportunity", opportunity.name, ignore_communication_links)

	return opportunity.name
