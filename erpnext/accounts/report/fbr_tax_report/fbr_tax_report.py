# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt

class FBRInvoiceWiseTaxes(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		data = self.get_data()
		columns = self.get_columns()
		return columns, data

	def get_columns(self):
		all_columns = [
			{
				"label": _("Date"),
				"fieldtype": "Date",
				"fieldname": "posting_date",
				"width": 80
			},
			{
				"label": _("Sales Invoice"),
				"fieldtype": "Link",
				"fieldname": "invoice",
				"options": "Sales Invoice",
				"width": 120
			},
			{
				"label": _("Inv #"),
				"fieldtype": "Int",
				"fieldname": "stin",
				"width": 60
			},
			{
				"label": _("Net Total"),
				"fieldtype": "Currency",
				"fieldname": "base_net_total",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Grand Total"),
				"fieldtype": "Currency",
				"fieldname": "base_grand_total",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Total Taxes"),
				"fieldtype": "Currency",
				"fieldname": "base_total_taxes_and_charges",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _(self.filters.party_type),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": self.filters.party_type,
				"width": 200
			},
			{
				"label": _(self.filters.party_type + "Name"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 110
			},
			{
				"label": _("NTN"),
				"fieldtype": "Data",
				"fieldname": "tax_id",
				"width": 100
			},
			{
				"label": _("CNIC"),
				"fieldtype": "Data",
				"fieldname": "tax_cnic",
				"width": 120
			},
			{
				"label": _("STRN"),
				"fieldtype": "Data",
				"fieldname": "tax_strn",
				"width": 120
			}
		]
		for (description, rate) in self.tax_columns:
			all_columns.append({
				"label": _(get_tax_label(description, rate)),
				"fieldtype": "Currency",
				"fieldname": get_tax_fieldname(description, rate),
				"options": "Company:company:default_currency",
				"width": 120
			})

		if self.filters.detail_by == "Customer":
			fieldnames = ['party', 'party_name', 'tax_id', 'tax_cnic', 'tax_strn', 'base_net_total', 'base_grand_total']
			for (description, rate) in self.tax_columns:
				fieldnames.append(get_tax_fieldname(description, rate))
			fieldnames += ['base_total_taxes_and_charges']
		else:
			fieldnames = ['posting_date', 'invoice', 'stin', 'base_net_total', 'base_grand_total']
			for (description, rate) in self.tax_columns:
				fieldnames.append(get_tax_fieldname(description, rate))
			fieldnames += ['base_total_taxes_and_charges', 'party', 'party_name', 'tax_id', 'tax_cnic', 'tax_strn']

		columns = [list(filter(lambda d: d['fieldname'] == f, all_columns))[0] for f in fieldnames]

		if self.party_naming_by != "Naming Series":
			columns = list(filter(lambda d: d['fieldname'] != 'party_name', columns))

		return columns

	def get_data(self):
		conditions = "and i.customer = %(party)s" if self.filters.party else ""

		self.invoices = frappe.db.sql("""
			select
				i.name as invoice, i.posting_date, i.base_net_total, i.base_grand_total, i.base_total_taxes_and_charges,
				i.customer as party, i.customer_name as party_name, c.tax_id, c.tax_cnic, c.tax_strn, i.stin
			from `tabSales Invoice` i
			left join `tabCustomer` c on c.name = i.customer
			where i.docstatus = 1 and i.company = %(company)s and i.posting_date between %(from_date)s and %(to_date)s
				and abs(i.base_total_taxes_and_charges) > 0 {0}
			order by i.posting_date, i.name
		""".format(conditions), self.filters, as_dict=1)

		invoice_names = [d.invoice for d in self.invoices]

		if invoice_names:
			taxes = frappe.db.sql("""
				select
					parent as invoice, description, rate, sum(base_tax_amount_after_discount_amount) as amount
				from `tabSales Taxes and Charges`
				where parent in ({0}) and abs(base_tax_amount_after_discount_amount) > 0
				group by parent, description, rate
			""".format(", ".join(['%s'] * len(invoice_names))), invoice_names, as_dict=1)
		else:
			taxes = []

		self.tax_map = frappe._dict()
		self.tax_columns = []
		for tax in taxes:
			tax_column = (tax.description, flt(tax.rate))
			self.tax_map.setdefault(tax.invoice, frappe._dict())[tax_column] = tax.amount
			if tax_column not in self.tax_columns:
				self.tax_columns.append(tax_column)

		self.tax_columns = sorted(self.tax_columns, key=lambda d: d[1], reverse=True)

		for d in self.invoices:
			for (description, rate) in self.tax_columns:
				fieldname = get_tax_fieldname(description, rate)
				d[fieldname] = flt(self.tax_map.get(d.invoice, frappe._dict()).get((description, rate)))

		# Customer aggregates
		self.customer_aggregate = frappe._dict()
		if self.filters.detail_by == "Customer":
			party_fields = ['party', 'tax_id', 'tax_cnic', 'tax_strn']
			aggregate_fields = ['base_net_total', 'base_grand_total', 'base_total_taxes_and_charges']
			for (description, rate) in self.tax_columns:
				aggregate_fields.append(get_tax_fieldname(description, rate))

			customer_row_template = frappe._dict()
			for f in aggregate_fields:
				customer_row_template[f] = 0.0

			for d in self.invoices:
				if d.party not in self.customer_aggregate:
					self.customer_aggregate[d.party] = customer_row_template.copy()
					for f in party_fields:
						self.customer_aggregate[d.party][f] = d[f]

				for f in aggregate_fields:
					self.customer_aggregate[d.party][f] += d[f]

			return list(self.customer_aggregate.values())
		else:
			return self.invoices


def get_tax_fieldname(description, rate):
	return "tax_{0}_{1}".format(scrub(description), scrub(frappe.format(flt(rate))))


def get_tax_label(description, rate):
	if rate:
		return "{0} ({1}%)".format(description, frappe.format(flt(rate)))
	else:
		return description

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return FBRInvoiceWiseTaxes(filters).run(args)
