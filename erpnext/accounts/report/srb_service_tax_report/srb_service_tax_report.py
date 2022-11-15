# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt, cint
from erpnext import get_company_currency
from frappe.model.meta import get_field_precision
import json


class FBRInvoiceWiseTaxes(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		self.filters.service_tax_account = frappe.get_cached_value('Company', self.filters.company, "service_tax_account")

		self.filters.tax_accounts = []
		if self.filters.service_tax_account:
			self.filters.tax_accounts.append(self.filters.service_tax_account)

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		data = self.get_data()
		columns = self.get_columns()
		return columns, data, None, None, None, cint(self.filters.for_export)

	def get_columns(self):
		columns = [
			{
				"label": _("Sr."),
				"fieldtype": "Int",
				"fieldname": "sr_no",
				"width": 40,
				"hide_for_view": 1
			},
			{
				"label": _("NTN"),
				"fieldtype": "Data",
				"fieldname": "tax_id",
				"width": 75
			},
			{
				"label": _("CNIC"),
				"fieldtype": "Data",
				"fieldname": "tax_cnic",
				"width": 110
			},
			{
				"label": _("Name of Buyer"),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": self.filters.party_type,
				"width": 80 if self.party_naming_by == "Naming Series" else 200,
				"hide_for_export": 1
			},
			{
				"label": _("Name of Buyer"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 200
			},
			{
				"label": _("District of Buyer"),
				"fieldtype": "Data",
				"fieldname": "city",
				"editable": 1,
				"width": 90
			},
			{
				"label": _("Buyer Type"),
				"fieldtype": "Data",
				"fieldname": "buyer_type",
				"width": 90
			},
			{
				"label": _("Document Type"),
				"fieldtype": "Data",
				"fieldname": "document_type",
				"width": 50,
				"hide_for_view": 1
			},
			{
				"label": _("Sales Invoice"),
				"fieldtype": "Link",
				"fieldname": "invoice",
				"options": "Sales Invoice",
				"width": 90,
				"hide_for_export": 1
			},
			{
				"label": _("Document Number"),
				"fieldtype": "Int",
				"fieldname": "stin",
				"width": 60
			},
			{
				"label": _("Document Date"),
				"fieldtype": "Data",
				"fieldname": "posting_date",
				"width": 80
			},
			{
				"label": _("HS Code"),
				"fieldtype": "Data",
				"fieldname": "hscode",
				"width": 80,
				"hide_for_view": 1
			},
			{
				"label": _("Sale Type"),
				"fieldtype": "Data",
				"fieldname": "sale_type",
				"width": 80,
				"hide_for_view": 1
			},
			{
				"label": _("Rate"),
				"fieldtype": "Percent",
				"fieldname": "rate",
				"width": 50
			},
			{
				"label": _("Value of Sales Excluding Sales Tax"),
				"fieldtype": "Currency",
				"fieldname": "base_taxable_total",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Sales Tax Involved"),
				"fieldtype": "Currency",
				"fieldname": "service_tax",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("ST Withheld at Source"),
				"fieldtype": "Data",
				"fieldname": "withheld_amount",
				"width": 80,
				"hide_for_view": 1
			},
		]

		if self.party_naming_by != "Naming Series" and not cint(self.filters.for_export):
			columns = list(filter(lambda d: d['fieldname'] != 'party_name', columns))

		if cint(self.filters.for_export):
			columns = list(filter(lambda d: not d.get("hide_for_export"), columns))
		else:
			columns = list(filter(lambda d: not d.get("hide_for_view"), columns))

		return columns

	def get_data(self):
		self.get_invoices()
		self.process_invoice_map()

		for i, d in enumerate(self.invoices):
			d.sr_no = i+1

		return self.invoices

	def get_invoices(self):
		conditions = "and i.bill_to = %(party)s" if self.filters.party else ""

		if self.filters.tax_accounts:
			self.invoices = frappe.db.sql("""
				select
					i.name as invoice, i.stin, DATE_FORMAT(i.posting_date, '%%d/%%m/%%Y') as posting_date,
					addr.city, addr.name as address_name,
					i.bill_to as party, i.bill_to_name as party_name,
					c.tax_id, c.tax_cnic, i.conversion_rate
				from `tabSales Invoice` i
				left join `tabCustomer` c on c.name = i.bill_to
				left join `tabAddress` addr on addr.name = i.customer_address
				where i.docstatus = 1 and i.company = %(company)s and i.posting_date between %(from_date)s and %(to_date)s
					and ifnull(i.is_return, 0) = 0 and exists(select tax.name from `tabSales Taxes and Charges` tax
						where tax.parent = i.name and tax.account_head in ({0}) and tax.base_tax_amount_after_discount_amount != 0)
					{1}
				order by i.posting_date, i.stin
			""".format(",".join([frappe.db.escape(d) for d in self.filters.tax_accounts]), conditions), self.filters, as_dict=1)
		else:
			self.invoices = []

		self.invoices_map = {}
		for d in self.invoices:
			d.base_taxable_total = 0
			d.base_total_after_taxes = 0
			d.service_tax = 0
			d.buyer_type = "End_Consumer"
			d.sale_type = "Services"
			d.document_type = "SI"
			d.hscode = "98201000"
			self.invoices_map[d.invoice] = frappe._dict({
				'invoice': d, 'items': [], 'taxes': []
			})

		invoice_names = list(self.invoices_map.keys())

		if invoice_names:
			invoice_items = frappe.db.sql("""
				select i.parent as invoice, i.base_taxable_amount, i.item_tax_detail
				from `tabSales Invoice Item` i
				where i.parent in %s
			""", [invoice_names], as_dict=1)

			for d in invoice_items:
				self.invoices_map[d.invoice]['items'].append(d)

		if invoice_names and self.filters.tax_accounts:
			taxes = frappe.db.sql("""
				select
					name, parent as invoice, rate, account_head
				from `tabSales Taxes and Charges`
				where parent in %s and account_head in %s
					and abs(base_tax_amount_after_discount_amount) > 0
				group by parent, account_head
			""", [invoice_names, self.filters.tax_accounts], as_dict=1)

			for tax in taxes:
				self.invoices_map[tax.invoice]['taxes'].append(tax)

	def process_invoice_map(self):
		company_currency = get_company_currency(self.filters.company)
		tax_precision = get_field_precision(frappe.get_meta("Sales Taxes and Charges").get_field("base_tax_amount"),
			company_currency)
		taxable_precision = get_field_precision(frappe.get_meta("Sales Invoice").get_field("base_taxable_total"),
			company_currency)
		total_precision = get_field_precision(frappe.get_meta("Sales Invoice").get_field("base_total_after_taxes"),
			company_currency)

		for inv_obj in self.invoices_map.values():
			for item in inv_obj['items']:
				item_tax_detail = json.loads(item.item_tax_detail or '{}')
				has_tax = False

				for tax in inv_obj['taxes']:
					tax_field = self.get_tax_field(tax.account_head)
					if tax_field and item_tax_detail.get(tax.name):
						has_tax = True
						inv_obj['invoice'][tax_field] += flt(item_tax_detail.get(tax.name))

				if has_tax:
					inv_obj['invoice']['base_taxable_total'] += item.base_taxable_amount

			for tax in inv_obj['taxes']:
				tax_field = self.get_tax_field(tax.account_head)

				if tax_field:
					inv_obj['invoice'][tax_field] = flt(inv_obj['invoice'][tax_field], tax_precision)
					inv_obj['invoice'][tax_field] = flt(inv_obj['invoice'][tax_field] * inv_obj['invoice'].conversion_rate,
						tax_precision)

					inv_obj['invoice']['base_total_after_taxes'] += inv_obj['invoice'][tax_field]

			inv_obj['invoice']['rate'] = flt(inv_obj['invoice']['service_tax'] / inv_obj['invoice']['base_taxable_total'] * 100\
				if inv_obj['invoice']['base_taxable_total'] else 0, 2)

			inv_obj['invoice']['base_total_after_taxes'] += inv_obj['invoice']['base_taxable_total']
			inv_obj['invoice']['base_taxable_total'] = flt(inv_obj['invoice']['base_taxable_total'], taxable_precision)
			inv_obj['invoice']['base_total_after_taxes'] = flt(inv_obj['invoice']['base_total_after_taxes'], total_precision)

	def get_tax_field(self, account_head):
		tax_field = ''
		if account_head == self.filters.service_tax_account:
			tax_field = 'service_tax'

		return tax_field


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return FBRInvoiceWiseTaxes(filters).run(args)
