# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from datetime import date

def execute(filters=None):
	return Gstr2Report(filters).run()

class Gstr2Report(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_columns()
		self.get_data()
		return self.columns, self.data

	def get_data(self):
		self.data = []
		self.get_gst_accounts()
		self.get_invoice_data()

		if not self.invoices: return

		self.get_invoice_items()
		self.get_items_based_on_tax_rate()
		invoice_fields = [d["fieldname"] for d in self.invoice_columns]


		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			invoice_details = self.invoices.get(inv)
			for x in xrange(1,10):
				print(invoice_details)
			for rate, items in items_based_on_rate.items():
				row = []
				for fieldname in invoice_fields:
					if fieldname == "invoice_value":
						row.append(invoice_details.base_rounded_total or invoice_details.base_grand_total)
					else:
						row.append(invoice_details.get(fieldname))

				row += [rate,
					sum([net_amount for item_code, net_amount in self.invoice_items.get(inv).items()
						if item_code in items]),
					self.invoice_cess.get(inv),
				]


				if self.filters.get("type_of_business") ==  "CDNR":
					row.append("Y" if invoice_details.posting_date <= date(2017, 7, 1) else "N")
					row.append("C" if invoice_details.return_against else "R")

				self.data.append(row)

	def get_invoice_data(self):
		self.invoices = frappe._dict()
		conditions = self.get_conditions()

		invoice_data = frappe.db.sql("""
			select
				name as invoice_number,
				supplier_name,
				posting_date,
				base_grand_total,
				base_rounded_total,
				supplier_gstin,
				place_of_supply,
				ecommerce_gstin,
				reverse_charge,
				invoice_type,
				return_against,
				is_return,
				invoice_type,
				export_type,
				port_code,
				shipping_bill_number,
				shipping_bill_date,
				reason_for_issuing_document,
				eligibility_for_itc,
				itc_integrated_tax,
				itc_central_tax,
				itc_state_tax,
				itc_cess_amount
			from `tabPurchase Invoice`
			where docstatus = 1 %s
			order by posting_date desc
			""" % (conditions), self.filters, as_dict=1)

		for d in invoice_data:
			self.invoices.setdefault(d.invoice_number, d)

	def get_conditions(self):
		conditions = ""

		for opts in (("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s")):
				if self.filters.get(opts[0]):
					conditions += opts[1]

		if self.filters.get("type_of_business") ==  "B2B":
			conditions += "and invoice_type != 'Export' and is_return != 1 "

		elif self.filters.get("type_of_business") ==  "CDNR":
			conditions += """ and is_return = 1 """

		return conditions

	def get_invoice_items(self):
		self.invoice_items = frappe._dict()
		items = frappe.db.sql("""
			select item_code, parent, base_net_amount
			from `tabPurchase Invoice Item`
			where parent in (%s)
		""" % (', '.join(['%s']*len(self.invoices))), tuple(self.invoices), as_dict=1)

		for d in items:
			self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, d.base_net_amount)

	def get_items_based_on_tax_rate(self):
		tax_details = frappe.db.sql("""
			select
				parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
			from `tabPurchase Taxes and Charges`
			where
				parenttype = 'Purchase Invoice' and docstatus = 1
				and parent in (%s)

			order by account_head
		""" % (', '.join(['%s']*len(self.invoices.keys()))), tuple(self.invoices.keys()))

		self.items_based_on_tax_rate = {}
		self.invoice_cess = frappe._dict()
		unidentified_gst_accounts = []

		for parent, account, item_wise_tax_detail, tax_amount in tax_details:
			if account in self.gst_accounts.cess_account:
				self.invoice_cess.setdefault(parent, tax_amount)
			else:
				if item_wise_tax_detail:
					try:
						item_wise_tax_detail = json.loads(item_wise_tax_detail)
						cgst_or_sgst = False
						if account in self.gst_accounts.cgst_account \
							or account in self.gst_accounts.sgst_account:
							cgst_or_sgst = True

						if not (cgst_or_sgst or account in self.gst_accounts.igst_account):
							if "gst" in account.lower() and account not in unidentified_gst_accounts:
								unidentified_gst_accounts.append(account)
							continue

						for item_code, tax_amounts in item_wise_tax_detail.items():
							tax_rate = tax_amounts[0]
							if cgst_or_sgst:
								tax_rate *= 2

							rate_based_dict = self.items_based_on_tax_rate.setdefault(parent, {})\
								.setdefault(tax_rate, [])
							if item_code not in rate_based_dict:
								rate_based_dict.append(item_code)
					except ValueError:
						continue
		if unidentified_gst_accounts:
			frappe.msgprint(_("Following accounts might be selected in GST Settings:")
				+ "<br>" + "<br>".join(unidentified_gst_accounts), alert=True)

	def get_gst_accounts(self):
		self.gst_accounts = frappe._dict()
		gst_settings_accounts = frappe.get_list("GST Account",
			filters={"parent": "GST Settings", "company": self.filters.company},
			fields=["cgst_account", "sgst_account", "igst_account", "cess_account"])

		if not gst_settings_accounts:
			frappe.throw(_("Please set GST Accounts in GST Settings"))

		for d in gst_settings_accounts:
			for acc, val in d.items():
				self.gst_accounts.setdefault(acc, []).append(val)

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
					"fieldname": "invoice_type",
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
