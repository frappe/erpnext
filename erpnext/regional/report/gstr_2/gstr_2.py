# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from datetime import date

import frappe

from erpnext.regional.report.gstr_1.gstr_1 import Gstr1Report


def execute(filters=None):
	return Gstr2Report(filters).run()

class Gstr2Report(Gstr1Report):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctype = "Purchase Invoice"
		self.tax_doctype = "Purchase Taxes and Charges"
		self.select_columns = """
			name as invoice_number,
			supplier_name,
			posting_date,
			base_grand_total,
			base_rounded_total,
			supplier_gstin,
			place_of_supply,
			ecommerce_gstin,
			reverse_charge,
			gst_category,
			return_against,
			is_return,
			gst_category,
			export_type,
			reason_for_issuing_document,
			eligibility_for_itc,
			itc_integrated_tax,
			itc_central_tax,
			itc_state_tax,
			itc_cess_amount
		"""

	def get_data(self):
		self.get_igst_invoices()
		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			invoice_details = self.invoices.get(inv)
			for rate, items in items_based_on_rate.items():
				if rate or invoice_details.get('gst_category') == 'Registered Composition':
					if inv not in self.igst_invoices:
						rate = rate / 2
						row, taxable_value = self.get_row_data_for_invoice(inv, invoice_details, rate, items)
						tax_amount = taxable_value * rate / 100
						row += [0, tax_amount, tax_amount]
					else:
						row, taxable_value = self.get_row_data_for_invoice(inv, invoice_details, rate, items)
						tax_amount = taxable_value * rate / 100
						row += [tax_amount, 0, 0]

					row += [
						self.invoice_cess.get(inv),
						invoice_details.get('eligibility_for_itc'),
						invoice_details.get('itc_integrated_tax'),
						invoice_details.get('itc_central_tax'),
						invoice_details.get('itc_state_tax'),
						invoice_details.get('itc_cess_amount')
					]
					if self.filters.get("type_of_business") ==  "CDNR":
						row.append("Y" if invoice_details.posting_date <= date(2017, 7, 1) else "N")
						row.append("C" if invoice_details.return_against else "R")

					self.data.append(row)

	def get_igst_invoices(self):
		self.igst_invoices = []
		for d in self.tax_details:
			is_igst = True if d[1] in self.gst_accounts.igst_account else False
			if is_igst and d[0] not in self.igst_invoices:
				self.igst_invoices.append(d[0])

	def get_conditions(self):
		conditions = ""

		for opts in (("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s")):
				if self.filters.get(opts[0]):
					conditions += opts[1]

		if self.filters.get("type_of_business") ==  "B2B":
			conditions += "and ifnull(gst_category, '') in ('Registered Regular', 'Deemed Export', 'SEZ', 'Registered Composition') and is_return != 1 "

		elif self.filters.get("type_of_business") ==  "CDNR":
			conditions += """ and is_return = 1 """

		return conditions

	def get_columns(self):
		self.tax_columns = [
			{
				"fieldname": "rate",
				"label": "Rate",
				"fieldtype": "Int",
				"width": 60
			},
			{
				"fieldname": "taxable_value",
				"label": "Taxable Value",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "integrated_tax_paid",
				"label": "Integrated Tax Paid",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "central_tax_paid",
				"label": "Central Tax Paid",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "state_tax_paid",
				"label": "State/UT Tax Paid",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "cess_amount",
				"label": "Cess Paid",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "eligibility_for_itc",
				"label": "Eligibility For ITC",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"fieldname": "itc_integrated_tax",
				"label": "Availed ITC Integrated Tax",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "itc_central_tax",
				"label": "Availed ITC Central Tax",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "itc_state_tax",
				"label": "Availed ITC State/UT Tax",
				"fieldtype": "Currency",
				"width": 100
			},
			{
				"fieldname": "itc_cess_amount",
				"label": "Availed ITC Cess ",
				"fieldtype": "Currency",
				"width": 100
			}
		]
		self.other_columns = []

		if self.filters.get("type_of_business") ==  "B2B":
			self.invoice_columns = [
				{
					"fieldname": "supplier_gstin",
					"label": "GSTIN of Supplier",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Date",
					"width": 120
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "reverse_charge",
					"label": "Reverse Charge",
					"fieldtype": "Data",
					"width": 80
				},
				{
					"fieldname": "gst_category",
					"label": "Invoice Type",
					"fieldtype": "Data",
					"width": 80
				}
			]
		elif self.filters.get("type_of_business") ==  "CDNR":
			self.invoice_columns = [
				{
					"fieldname": "supplier_gstin",
					"label": "GSTIN of Supplier",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_number",
					"label": "Note/Refund Voucher Number",
					"fieldtype": "Link",
					"options": "Purchase Invoice"
				},
				{
					"fieldname": "posting_date",
					"label": "Note/Refund Voucher date",
					"fieldtype": "Date",
					"width": 120
				},
				{
					"fieldname": "return_against",
					"label": "Invoice/Advance Payment Voucher Number",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice/Advance Payment Voucher date",
					"fieldtype": "Date",
					"width": 120
				},
				{
					"fieldname": "reason_for_issuing_document",
					"label": "Reason For Issuing document",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "supply_type",
					"label": "Supply Type",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120
				}
			]
			self.other_columns = [
				{
					"fieldname": "pre_gst",
					"label": "PRE GST",
					"fieldtype": "Data",
					"width": 50
				},
				{
					"fieldname": "document_type",
					"label": "Document Type",
					"fieldtype": "Data",
					"width": 50
				}
			]
		self.columns = self.invoice_columns + self.tax_columns + self.other_columns
