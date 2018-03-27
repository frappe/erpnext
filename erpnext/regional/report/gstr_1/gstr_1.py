# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import flt
from datetime import date

def execute(filters=None):
	return Gstr1Report(filters).run()

class Gstr1Report(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctype = "Sales Invoice"
		self.tax_doctype = "Sales Taxes and Charges"
		self.select_columns = """
			name as invoice_number,
			customer_name,
			posting_date,
			base_grand_total,
			base_rounded_total,
			customer_gstin,
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
			reason_for_issuing_document
		"""
		self.customer_type = "Company" if self.filters.get("type_of_business") ==  "B2B" else "Individual"

	def run(self):
		self.get_columns()
		self.get_gst_accounts()
		self.get_invoice_data()

		if self.invoices:
			self.get_invoice_items()
			self.get_items_based_on_tax_rate()
			self.invoice_fields = [d["fieldname"] for d in self.invoice_columns]
			self.get_data()

		return self.columns, self.data

	def get_data(self):
		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			invoice_details = self.invoices.get(inv)
			for rate, items in items_based_on_rate.items():
				row, taxable_value = self.get_row_data_for_invoice(inv, invoice_details, rate, items)
				if self.filters.get("type_of_business") ==  "B2C Small":
					row.append("E" if invoice_details.ecommerce_gstin else "OE")

				if self.filters.get("type_of_business") ==  "CDNR":
					row.append("Y" if invoice_details.posting_date <= date(2017, 7, 1) else "N")
					row.append("C" if invoice_details.return_against else "R")

				self.data.append(row)

	def get_row_data_for_invoice(self, invoice, invoice_details, tax_rate, items):
		row = []
		for fieldname in self.invoice_fields:
			if self.filters.get("type_of_business") ==  "CDNR" and fieldname == "invoice_value":
				row.append(abs(invoice_details.base_rounded_total) or abs(invoice_details.base_grand_total))
			elif fieldname == "invoice_value":
				row.append(invoice_details.base_rounded_total or invoice_details.base_grand_total)
			else:
				row.append(invoice_details.get(fieldname))

		taxable_value = sum([abs(net_amount)
			for item_code, net_amount in self.invoice_items.get(invoice).items() if item_code in items])
		row += [tax_rate, taxable_value]

		return row, taxable_value

	def get_invoice_data(self):
		self.invoices = frappe._dict()
		conditions = self.get_conditions()
		invoice_data = frappe.db.sql("""
			select
				{select_columns}
			from `tab{doctype}`
			where docstatus = 1 {where_conditions}
			order by posting_date desc
			""".format(select_columns=self.select_columns, doctype=self.doctype,
				where_conditions=conditions), self.filters, as_dict=1)

		for d in invoice_data:
			self.invoices.setdefault(d.invoice_number, d)

	def get_conditions(self):
		conditions = ""

		for opts in (("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s")):
				if self.filters.get(opts[0]):
					conditions += opts[1]

		customers = frappe.get_all("Customer", filters={"customer_type": self.customer_type})

		if self.filters.get("type_of_business") ==  "B2B":
			conditions += """ and ifnull(invoice_type, '') != 'Export' and is_return != 1
				and customer in ('{0}')""".format("', '".join([frappe.db.escape(c.name) for c in customers]))

		if self.filters.get("type_of_business") in ("B2C Large", "B2C Small"):
			b2c_limit = frappe.db.get_single_value('GSt Settings', 'b2c_limit')
			if not b2c_limit:
				frappe.throw(_("Please set B2C Limit in GST Settings."))

		if self.filters.get("type_of_business") ==  "B2C Large":
			conditions += """ and SUBSTR(place_of_supply, 1, 2) != SUBSTR(company_gstin, 1, 2)
				and grand_total > {0} and is_return != 1 and customer in ('{1}')""".\
					format(flt(b2c_limit), "', '".join([frappe.db.escape(c.name) for c in customers])	)
					
		elif self.filters.get("type_of_business") ==  "B2C Small":
			conditions += """ and (
				SUBSTR(place_of_supply, 1, 2) = SUBSTR(company_gstin, 1, 2)
					or grand_total <= {0}) and is_return != 1 and customer in ('{1}')""".\
						format(flt(b2c_limit), "', '".join([frappe.db.escape(c.name) for c in customers]))

		elif self.filters.get("type_of_business") ==  "CDNR":
			conditions += """ and is_return = 1 """

		elif self.filters.get("type_of_business") ==  "EXPORT":
			conditions += """ and is_return !=1 and invoice_type = 'Export' """
		return conditions

	def get_invoice_items(self):
		self.invoice_items = frappe._dict()
		items = frappe.db.sql("""
			select item_code, parent, base_net_amount
			from `tab%s Item`
			where parent in (%s)
		""" % (self.doctype, ', '.join(['%s']*len(self.invoices))), tuple(self.invoices), as_dict=1)

		for d in items:
			self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, d.base_net_amount)

	def get_items_based_on_tax_rate(self):
		self.tax_details = frappe.db.sql("""
			select
				parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
			from `tab%s`
			where
				parenttype = %s and docstatus = 1
				and parent in (%s)
			order by account_head
		""" % (self.tax_doctype, '%s', ', '.join(['%s']*len(self.invoices.keys()))),
			tuple([self.doctype] + self.invoices.keys()))

		self.items_based_on_tax_rate = {}
		self.invoice_cess = frappe._dict()
		unidentified_gst_accounts = []
		for parent, account, item_wise_tax_detail, tax_amount in self.tax_details:
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

							rate_based_dict = self.items_based_on_tax_rate\
								.setdefault(parent, {}).setdefault(tax_rate, [])
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
			}
		]
		self.other_columns = []

		if self.filters.get("type_of_business") ==  "B2B":
			self.invoice_columns = [
				{
					"fieldname": "customer_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150
				},
				{
					"fieldname": "customer_name",
					"label": "Receiver Name",
					"fieldtype": "Data",
					"width":100
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":100
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Date",
					"width":80
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width":100
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place of Supply",
					"fieldtype": "Data",
					"width":100
				},
				{
					"fieldname": "reverse_charge",
					"label": "Reverse Charge",
					"fieldtype": "Data"
				},
				{
					"fieldname": "invoice_type",
					"label": "Invoice Type",
					"fieldtype": "Data"
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width":120
				}
			]
			self.other_columns = [
					{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
					}
				]

		elif self.filters.get("type_of_business") ==  "B2C Large":
			self.invoice_columns = [
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Date",
					"width": 100
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 100
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130
				}
			]
			self.other_columns = [
					{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
					}
				]
		elif self.filters.get("type_of_business") ==  "CDNR":
			self.invoice_columns = [
				{
					"fieldname": "customer_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150
				},
				{
					"fieldname": "customer_name",
					"label": "Receiver Name",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "return_against",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice/Advance Receipt date",
					"fieldtype": "Date",
					"width": 120
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice/Advance Receipt date",
					"fieldtype": "Date",
					"width": 120
				},
				{
					"fieldname": "reason_for_issuing_document",
					"label": "Reason For Issuing document",
					"fieldtype": "Data",
					"width": 140
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place of Supply",
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
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
				},
				{
					"fieldname": "pre_gst",
					"label": "PRE GST",
					"fieldtype": "Data",
					"width": 80
				},
				{
					"fieldname": "document_type",
					"label": "Document Type",
					"fieldtype": "Data",
					"width": 80
				}
			]
		elif self.filters.get("type_of_business") ==  "B2C Small":
			self.invoice_columns = [
				{
					"fieldname": "place_of_supply",
					"label": "Place of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130
				}
			]
			self.other_columns = [
				{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
				},
				{
					"fieldname": "type",
					"label": "Type",
					"fieldtype": "Data",
					"width": 50
				}
			]
		elif self.filters.get("type_of_business") ==  "EXPORT":
			self.invoice_columns = [
				{
					"fieldname": "export_type",
					"label": "Export Type",
					"fieldtype": "Data",
					"width":120
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":120
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
					"fieldname": "port_code",
					"label": "Port Code",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "shipping_bill_number",
					"label": "Shipping Bill Number",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "shipping_bill_date",
					"label": "Shipping Bill Date",
					"fieldtype": "Date",
					"width": 120
				}
			]
		self.columns = self.invoice_columns + self.tax_columns + self.other_columns
