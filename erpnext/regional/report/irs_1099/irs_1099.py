# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, nowdate
from frappe.utils.data import fmt_money
from frappe.utils.jinja import render_template
from frappe.utils.pdf import get_pdf
from frappe.utils.print_format import read_multi_pdf
from pypdf import PdfWriter

from erpnext.accounts.utils import get_fiscal_year

IRS_1099_FORMS_FILE_EXTENSION = ".pdf"


def execute(filters=None):
	filters = filters if isinstance(filters, frappe._dict) else frappe._dict(filters)
	if not filters:
		filters.setdefault("fiscal_year", get_fiscal_year(nowdate())[0])
		filters.setdefault("company", frappe.db.get_default("company"))

	frappe.has_permission("Company", doc=filters.company, throw=True)
	validate_company_region(filters.company)

	columns = get_columns()

	payments = get_payments(filters).as_("payments")
	s = frappe.qb.DocType("Supplier")
	query = (
		frappe.qb.from_(payments)
		.inner_join(s)
		.on(s.name == payments.supplier)
		.select(
			s.supplier_group.as_("supplier_group"),
			payments.supplier.as_("supplier"),
			s.tax_id.as_("tax_id"),
			Sum(payments.amount).as_("payments"),
		)
		.where(s.irs_1099 == 1)
		.groupby(payments.supplier, s.supplier_group, s.tax_id)
		.orderby(payments.supplier, order=frappe.qb.desc)
	)

	if filters.supplier_group:
		query = query.where(s.supplier_group == filters.supplier_group)

	data = query.run(as_dict=True)

	return columns, data


def validate_company_region(company):
	if frappe.get_cached_value("Company", company, "country") != "United States":
		frappe.throw(
			_(
				"The company {0} is not in the United States. IRS 1099 is only available for companies in the United States."
			).format(frappe.bold(company))
		)


def get_payments(filters):
	"""Supplier payments from the ledger, plus those made directly on paid Purchase Invoices."""
	gl = frappe.qb.DocType("GL Entry")
	ledger_payments = (
		frappe.qb.from_(gl)
		.select(gl.party.as_("supplier"), (gl.debit - gl.credit).as_("amount"))
		.where(
			(gl.fiscal_year == filters.fiscal_year)
			& (gl.party_type == "Supplier")
			& (gl.company == filters.company)
			& (gl.is_cancelled == 0)
			& is_payment_voucher(gl)
		)
	)

	pi = frappe.qb.DocType("Purchase Invoice")
	year_start, year_end = frappe.get_cached_value(
		"Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"]
	)
	invoice_payments = (
		frappe.qb.from_(pi)
		.select(pi.supplier, pi.base_paid_amount)
		.where(
			(pi.docstatus == 1)
			& (pi.is_paid == 1)
			& (pi.company == filters.company)
			& pi.posting_date.between(year_start, year_end)
		)
	)
	return ledger_payments.union_all(invoice_payments)


def is_payment_voucher(gl):
	"""Payment Entries and Journal Entries through a bank or cash account, so invoices and debit notes are left out."""
	account = frappe.qb.DocType("Journal Entry Account")
	bank_or_cash_journals = (
		frappe.qb.from_(account).select(account.parent).where(account.account_type.isin(["Bank", "Cash"]))
	)
	return (gl.voucher_type == "Payment Entry") | (
		(gl.voucher_type == "Journal Entry") & gl.voucher_no.isin(bank_or_cash_journals)
	)


def get_columns():
	return [
		{
			"fieldname": "supplier_group",
			"label": _("Supplier Group"),
			"fieldtype": "Link",
			"options": "Supplier Group",
			"width": 200,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 200,
		},
		{"fieldname": "tax_id", "label": _("Tax ID"), "fieldtype": "Data", "width": 200},
		{"fieldname": "payments", "label": _("Total Payments"), "fieldtype": "Currency", "width": 200},
	]


def get_payer_address_html(company):
	address = frappe.qb.DocType("Address")
	address_list = (
		frappe.qb.from_(address)
		.select(address.name)
		.where(address.is_your_company_address == 1)
		.orderby(Case().when(address.address_type == "Postal", 1).else_(0), order=frappe.qb.desc)
		.orderby(Case().when(address.address_type == "Billing", 1).else_(0), order=frappe.qb.desc)
		.orderby(address.name)  # deterministic LIMIT-1 tie-break across engines
		.limit(1)
		.run(as_dict=True)
	)

	address_display = ""
	if address_list:
		company_address = address_list[0]["name"]
		address_display = frappe.get_doc("Address", company_address).get_display()

	return address_display


def get_street_address_html(party_type, party):
	link = frappe.qb.DocType("Dynamic Link")
	address = frappe.qb.DocType("Address")
	address_list = (
		frappe.qb.from_(link)
		.inner_join(address)
		.on(address.name == link.parent)
		.select(link.parent)
		.where((link.parenttype == "Address") & (link.link_name == party))
		.orderby(Case().when(address.address_type == "Postal", 1).else_(0), order=frappe.qb.desc)
		.orderby(Case().when(address.address_type == "Billing", 1).else_(0), order=frappe.qb.desc)
		.orderby(link.parent)  # deterministic LIMIT-1 tie-break across engines
		.limit(1)
		.run(as_dict=True)
	)

	street_address = city_state = ""
	if address_list:
		supplier_address = address_list[0]["parent"]
		doc = frappe.get_doc("Address", supplier_address)

		if doc.address_line2:
			street_address = doc.address_line1 + "<br>\n" + doc.address_line2 + "<br>\n"
		else:
			street_address = doc.address_line1 + "<br>\n"

		city_state = doc.city + ", " if doc.city else ""
		city_state = city_state + doc.state + " " if doc.state else city_state
		city_state = city_state + doc.pincode if doc.pincode else city_state
		city_state += "<br>\n"

	return street_address, city_state
