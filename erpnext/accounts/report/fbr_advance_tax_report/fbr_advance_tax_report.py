# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt, cint

class FBRInvoiceWiseTaxes(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		self.filters.advance_tax_account = frappe.get_cached_value('Company', self.filters.company, "advance_tax_account")

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))
		if not self.filters.advance_tax_account:
			frappe.throw(_("Please set 'Advance Tax Account' for Company '{0}' first").format(self.filters.company))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		data = self.get_data()
		columns = self.get_columns()
		return columns, data, None, None, None, cint(self.filters.for_export)

	def get_columns(self):
		columns = [
			{
				"label": _("Payment Section"),
				"fieldtype": "Data",
				"fieldname": "payment_section",
				"width": 90
			},
			{
				"label": _("TaxPayer_NTN"),
				"fieldtype": "Data",
				"fieldname": "tax_id",
				"width": 70
			},
			{
				"label": _("TaxPayer_CNIC"),
				"fieldtype": "Data",
				"fieldname": "tax_cnic",
				"width": 110
			},
			{
				"label": _("TaxPayer_Name"),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": self.filters.party_type,
				"width": 200
			},
			{
				"label": _("TaxPayer_Name"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 110
			},
			{
				"label": _("TaxPayer_City"),
				"fieldtype": "Data",
				"fieldname": "city",
				"width": 100
			},
			{
				"label": _("TaxPayer_Address"),
				"fieldtype": "Data",
				"fieldname": "address",
				"width": 100
			},
			{
				"label": _("TaxPayer_Status"),
				"fieldtype": "Data",
				"fieldname": "customer_type",
				"width": 50,
			},
			{
				"label": _("TaxPayer_Business_Name"),
				"fieldtype": "Data",
				"fieldname": "business_name",
				"width": 100,
			},
			{
				"label": _("Taxable_Amount"),
				"fieldtype": "Currency",
				"fieldname": "taxable_amount",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Tax_Amount"),
				"fieldtype": "Currency",
				"fieldname": "tax_amount",
				"options": "Company:company:default_currency",
				"width": 110
			},
		]

		if not cint(self.filters.for_export):
			columns.append({
				"label": _("Average Rate"),
				"fieldtype": "Float",
				"fieldname": "rate",
				"width": 100
			})

		if self.party_naming_by != "Naming Series":
			columns = list(filter(lambda d: d['fieldname'] != 'party_name', columns))

		return columns

	def get_data(self):
		taxes = frappe.db.sql("""
			select
				i.name as invoice, i.customer as party, t.account_head, t.charge_type, t.row_id, t.idx, t.rate,
				t.base_tax_amount_after_discount_amount as tax_amount, t.base_total, i.base_net_total
			from `tabSales Taxes and Charges` t
			inner join `tabSales Invoice` i on i.name = t.parent
			where i.docstatus = 1 and i.company = %(company)s and i.posting_date between %(from_date)s and %(to_date)s
				and exists(select t2.name from `tabSales Taxes and Charges` t2
					where t2.parent = i.name and t2.parenttype = 'Sales Invoice'
					and t2.account_head = %(advance_tax_account)s and abs(t2.base_tax_amount_after_discount_amount) > 0)
		""", self.filters, as_dict=1)

		advance_tax_in_invoice = set()
		customer_rows = {}
		invoice_taxes_idx_map = {}
		advance_taxes = []

		# Make invoice tax idx map
		for tax in taxes:
			invoice_taxes = invoice_taxes_idx_map.setdefault(tax.invoice, {})
			if tax.idx in invoice_taxes:
				frappe.msgprint(_("There is a problem in Sales Invoice '{0}'. Duplicate row idx found!").format(tax.invoice))
			invoice_taxes[tax.idx] = tax

			if tax.account_head == self.filters.advance_tax_account:
				if tax.invoice in advance_tax_in_invoice:
					frappe.msgprint(_("Sales Invoice '{0}' has multiple Advance Tax rows!").format(tax.invoice))
				else:
					advance_tax_in_invoice.add(tax.invoice)
				advance_taxes.append(tax)

		# Calculate taxable amount and aggregate customer totals
		for tax in advance_taxes:
			if tax.charge_type != "On Previous Row Total":
				frappe.msgprint(_("Sales Invoice '{0}' has Advance Tax with charge type '{1}'. Expected 'On Previous Row Total' for Advance Tax!")
					.format(tax.invoice, tax.charge_type))

			tax.row_id = cint(tax.row_id)
			reference_tax = invoice_taxes_idx_map.get(tax.invoice, {}).get(tax.row_id)
			if tax.charge_type in ("On Previous Row Total", "On Previous Row Amount") and not reference_tax:
				frappe.throw(_("There is a problem with Sales Invoice '{0}'. Reference tax for calculating Taxable Amount could be found!")
					.format(tax.invoice))

			if tax.charge_type == "On Previous Row Total":
				tax.taxable_amount = reference_tax.base_total
			elif tax.charge_type == "On Previous Row Amount":
				tax.taxable_amount = reference_tax.tax_amount
			else:
				tax.taxable_amount = tax.base_net_total

			row = customer_rows.setdefault(tax.party, frappe._dict({
				"party": tax.party, "taxable_amount": 0, "tax_amount": 0, "rate": 0, "rate_count": 0
			}))
			row.taxable_amount += flt(tax.taxable_amount)
			row.tax_amount += flt(tax.tax_amount)
			if tax.rate:
				row.rate += flt(tax.rate)
				row.rate_count += 1

		customer_details = self.get_customer_details(list(customer_rows.keys()))
		for d in customer_rows.values():
			d.update(customer_details.get(d.party, {}))

			if d.rate_count:
				d.rate /= d.rate_count
				del d['rate_count']

				d.business_name = d.party

		result = sorted(customer_rows.values(), key=lambda d: d.party)
		for i, d in enumerate(result):
			d.sr_no = i+1

		return result

	def get_customer_details(self, customers):
		if not customers:
			return {}

		data = frappe.db.sql("""
			select
				c.name as party, c.tax_id, c.tax_cnic, c.customer_name as party_name, c.customer_type,
				addr.city, concat_ws(' ', addr.address_line1, addr.address_line2) as address
			from `tabCustomer` c
			left join `tabDynamic Link` l on l.parenttype='Address' and l.link_doctype='Customer' and l.link_name=c.name
			left join `tabAddress` addr on addr.name = l.parent and addr.address_type = 'Billing'
			where c.name in ({0})
		""".format(", ".join(['%s'] * len(customers))), customers, as_dict=1)

		customer_details = {}
		for d in data:
			customer_details.setdefault(d.party, d)

		return customer_details

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return FBRInvoiceWiseTaxes(filters).run(args)
