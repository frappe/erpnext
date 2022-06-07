# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

from erpnext.regional.india.utils import get_gst_accounts


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
			NULLIF(billing_address_gstin, '') as billing_address_gstin,
			place_of_supply,
			ecommerce_gstin,
			reverse_charge,
			return_against,
			is_return,
			is_debit_note,
			gst_category,
			export_type,
			port_code,
			shipping_bill_number,
			shipping_bill_date,
			reason_for_issuing_document,
			company_gstin
		"""

	def run(self):
		self.get_columns()
		self.gst_accounts = get_gst_accounts(self.filters.company, only_non_reverse_charge=1)
		self.get_invoice_data()

		if self.invoices:
			self.get_invoice_items()
			self.get_items_based_on_tax_rate()
			self.invoice_fields = [d["fieldname"] for d in self.invoice_columns]

		self.get_data()

		return self.columns, self.data

	def get_data(self):
		if self.filters.get("type_of_business") in ("B2C Small", "B2C Large"):
			self.get_b2c_data()
		elif self.filters.get("type_of_business") == "Advances":
			self.get_advance_data()
		elif self.filters.get("type_of_business") == "NIL Rated":
			self.get_nil_rated_invoices()
		elif self.invoices:
			for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
				invoice_details = self.invoices.get(inv)
				for rate, items in items_based_on_rate.items():
					row, taxable_value = self.get_row_data_for_invoice(inv, invoice_details, rate, items)

					if self.filters.get("type_of_business") in ("CDNR-REG", "CDNR-UNREG"):
						row.append("Y" if invoice_details.posting_date <= date(2017, 7, 1) else "N")
						row.append("C" if invoice_details.is_return else "D")

					if taxable_value:
						self.data.append(row)

	def get_advance_data(self):
		advances_data = {}
		advances = self.get_advance_entries()
		for entry in advances:
			# only consider IGST and SGST so as to avoid duplication of taxable amount
			if (
				entry.account_head in self.gst_accounts.igst_account
				or entry.account_head in self.gst_accounts.sgst_account
			):
				advances_data.setdefault((entry.place_of_supply, entry.rate), [0.0, 0.0])
				advances_data[(entry.place_of_supply, entry.rate)][0] += entry.amount * 100 / entry.rate
			elif entry.account_head in self.gst_accounts.cess_account:
				advances_data[(entry.place_of_supply, entry.rate)][1] += entry.amount

		for key, value in advances_data.items():
			row = [key[0], key[1], value[0], value[1]]
			self.data.append(row)

	def get_nil_rated_invoices(self):
		nil_exempt_output = [
			{
				"description": "Inter-State supplies to registered persons",
				"nil_rated": 0.0,
				"exempted": 0.0,
				"non_gst": 0.0,
			},
			{
				"description": "Intra-State supplies to registered persons",
				"nil_rated": 0.0,
				"exempted": 0.0,
				"non_gst": 0.0,
			},
			{
				"description": "Inter-State supplies to unregistered persons",
				"nil_rated": 0.0,
				"exempted": 0.0,
				"non_gst": 0.0,
			},
			{
				"description": "Intra-State supplies to unregistered persons",
				"nil_rated": 0.0,
				"exempted": 0.0,
				"non_gst": 0.0,
			},
		]

		for invoice, details in self.nil_exempt_non_gst.items():
			invoice_detail = self.invoices.get(invoice)
			if invoice_detail.get("gst_category") in ("Registered Regular", "Deemed Export", "SEZ"):
				if is_inter_state(invoice_detail):
					nil_exempt_output[0]["nil_rated"] += details[0]
					nil_exempt_output[0]["exempted"] += details[1]
					nil_exempt_output[0]["non_gst"] += details[2]
				else:
					nil_exempt_output[1]["nil_rated"] += details[0]
					nil_exempt_output[1]["exempted"] += details[1]
					nil_exempt_output[1]["non_gst"] += details[2]
			else:
				if is_inter_state(invoice_detail):
					nil_exempt_output[2]["nil_rated"] += details[0]
					nil_exempt_output[2]["exempted"] += details[1]
					nil_exempt_output[2]["non_gst"] += details[2]
				else:
					nil_exempt_output[3]["nil_rated"] += details[0]
					nil_exempt_output[3]["exempted"] += details[1]
					nil_exempt_output[3]["non_gst"] += details[2]

		self.data = nil_exempt_output

	def get_b2c_data(self):
		b2cs_output = {}

		if self.invoices:
			for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
				invoice_details = self.invoices.get(inv)
				for rate, items in items_based_on_rate.items():
					place_of_supply = invoice_details.get("place_of_supply")
					ecommerce_gstin = invoice_details.get("ecommerce_gstin")

					b2cs_output.setdefault(
						(rate, place_of_supply, ecommerce_gstin),
						{
							"place_of_supply": "",
							"ecommerce_gstin": "",
							"rate": "",
							"taxable_value": 0,
							"cess_amount": 0,
							"type": "",
							"invoice_number": invoice_details.get("invoice_number"),
							"posting_date": invoice_details.get("posting_date"),
							"invoice_value": invoice_details.get("base_grand_total"),
						},
					)

					row = b2cs_output.get((rate, place_of_supply, ecommerce_gstin))
					row["place_of_supply"] = place_of_supply
					row["ecommerce_gstin"] = ecommerce_gstin
					row["rate"] = rate
					row["taxable_value"] += sum(
						[
							abs(net_amount)
							for item_code, net_amount in self.invoice_items.get(inv).items()
							if item_code in items
						]
					)
					row["cess_amount"] += flt(self.invoice_cess.get(inv), 2)
					row["type"] = "E" if ecommerce_gstin else "OE"

			for key, value in b2cs_output.items():
				self.data.append(value)

	def get_row_data_for_invoice(self, invoice, invoice_details, tax_rate, items):
		row = []
		for fieldname in self.invoice_fields:
			if (
				self.filters.get("type_of_business") in ("CDNR-REG", "CDNR-UNREG")
				and fieldname == "invoice_value"
			):
				row.append(abs(invoice_details.base_rounded_total) or abs(invoice_details.base_grand_total))
			elif fieldname == "invoice_value":
				row.append(invoice_details.base_rounded_total or invoice_details.base_grand_total)
			elif fieldname in ("posting_date", "shipping_bill_date"):
				row.append(formatdate(invoice_details.get(fieldname), "dd-MMM-YY"))
			elif fieldname == "export_type":
				export_type = "WPAY" if invoice_details.get(fieldname) == "With Payment of Tax" else "WOPAY"
				row.append(export_type)
			else:
				row.append(invoice_details.get(fieldname))
		taxable_value = 0

		if invoice in self.cgst_sgst_invoices:
			division_factor = 2
		else:
			division_factor = 1

		for item_code, net_amount in self.invoice_items.get(invoice).items():
			if item_code in items:
				if self.item_tax_rate.get(invoice) and tax_rate / division_factor in self.item_tax_rate.get(
					invoice, {}
				).get(item_code, []):
					taxable_value += abs(net_amount)
				elif not self.item_tax_rate.get(invoice):
					taxable_value += abs(net_amount)
				elif tax_rate:
					taxable_value += abs(net_amount)
				elif (
					not tax_rate
					and (
						self.filters.get("type_of_business") == "EXPORT"
						or invoice_details.get("gst_category") == "SEZ"
					)
					and invoice_details.get("export_type") == "Without Payment of Tax"
				):
					taxable_value += abs(net_amount)

		row += [tax_rate or 0, taxable_value]

		for column in self.other_columns:
			if column.get("fieldname") == "cess_amount":
				row.append(flt(self.invoice_cess.get(invoice), 2))

		return row, taxable_value

	def get_invoice_data(self):
		self.invoices = frappe._dict()
		conditions = self.get_conditions()

		invoice_data = frappe.db.sql(
			"""
			select
				{select_columns}
			from `tab{doctype}`
			where docstatus = 1 {where_conditions}
			and is_opening = 'No'
			order by posting_date desc
			""".format(
				select_columns=self.select_columns, doctype=self.doctype, where_conditions=conditions
			),
			self.filters,
			as_dict=1,
		)

		for d in invoice_data:
			self.invoices.setdefault(d.invoice_number, d)

	def get_advance_entries(self):
		return frappe.db.sql(
			"""
			SELECT SUM(a.base_tax_amount) as amount, a.account_head, a.rate, p.place_of_supply
			FROM `tabPayment Entry` p, `tabAdvance Taxes and Charges` a
			WHERE p.docstatus = 1
			AND p.name = a.parent
			AND posting_date between %s and %s
			GROUP BY a.account_head, p.place_of_supply, a.rate
		""",
			(self.filters.get("from_date"), self.filters.get("to_date")),
			as_dict=1,
		)

	def get_conditions(self):
		conditions = ""

		for opts in (
			("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
			("company_address", " and company_address=%(company_address)s"),
			("company_gstin", " and company_gstin=%(company_gstin)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]

		if self.filters.get("type_of_business") == "B2B":
			conditions += "AND IFNULL(gst_category, '') in ('Registered Regular', 'Registered Composition', 'Deemed Export', 'SEZ') AND is_return != 1 AND is_debit_note !=1"

		if self.filters.get("type_of_business") in ("B2C Large", "B2C Small"):
			b2c_limit = frappe.db.get_single_value("GST Settings", "b2c_limit")
			if not b2c_limit:
				frappe.throw(_("Please set B2C Limit in GST Settings."))

		if self.filters.get("type_of_business") == "B2C Large":
			conditions += """ AND ifnull(SUBSTR(place_of_supply, 1, 2),'') != ifnull(SUBSTR(company_gstin, 1, 2),'')
				AND grand_total > {0} AND is_return != 1 AND is_debit_note !=1 AND gst_category ='Unregistered' """.format(
				flt(b2c_limit)
			)

		elif self.filters.get("type_of_business") == "B2C Small":
			conditions += """ AND (
				SUBSTR(place_of_supply, 1, 2) = SUBSTR(company_gstin, 1, 2)
					OR grand_total <= {0}) and is_return != 1 AND gst_category ='Unregistered' """.format(
				flt(b2c_limit)
			)

		elif self.filters.get("type_of_business") == "CDNR-REG":
			conditions += """ AND (is_return = 1 OR is_debit_note = 1) AND IFNULL(gst_category, '') in ('Registered Regular', 'Deemed Export', 'SEZ')"""

		elif self.filters.get("type_of_business") == "CDNR-UNREG":
			b2c_limit = frappe.db.get_single_value("GST Settings", "b2c_limit")
			conditions += """ AND ifnull(SUBSTR(place_of_supply, 1, 2),'') != ifnull(SUBSTR(company_gstin, 1, 2),'')
				AND (is_return = 1 OR is_debit_note = 1)
				AND IFNULL(gst_category, '') in ('Unregistered', 'Overseas')"""

		elif self.filters.get("type_of_business") == "EXPORT":
			conditions += """ AND is_return !=1 and gst_category = 'Overseas' """

		conditions += " AND IFNULL(billing_address_gstin, '') != company_gstin"

		return conditions

	def get_invoice_items(self):
		self.invoice_items = frappe._dict()
		self.item_tax_rate = frappe._dict()
		self.item_hsn_map = frappe._dict()
		self.nil_exempt_non_gst = {}

		# nosemgrep
		items = frappe.db.sql(
			"""
			select item_code, parent, taxable_value, base_net_amount, item_tax_rate, is_nil_exempt,
			gst_hsn_code, is_non_gst from `tab%s Item`
			where parent in (%s)
		"""
			% (self.doctype, ", ".join(["%s"] * len(self.invoices))),
			tuple(self.invoices),
			as_dict=1,
		)

		for d in items:
			self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, 0.0)
			self.item_hsn_map.setdefault(d.item_code, d.gst_hsn_code)
			self.invoice_items[d.parent][d.item_code] += d.get("taxable_value", 0) or d.get(
				"base_net_amount", 0
			)

			item_tax_rate = {}

			if d.item_tax_rate:
				item_tax_rate = json.loads(d.item_tax_rate)

				for account, rate in item_tax_rate.items():
					tax_rate_dict = self.item_tax_rate.setdefault(d.parent, {}).setdefault(d.item_code, [])
					tax_rate_dict.append(rate)

			if d.is_nil_exempt:
				self.nil_exempt_non_gst.setdefault(d.parent, [0.0, 0.0, 0.0])
				if item_tax_rate:
					self.nil_exempt_non_gst[d.parent][0] += d.get("taxable_value", 0)
				else:
					self.nil_exempt_non_gst[d.parent][1] += d.get("taxable_value", 0)
			elif d.is_non_gst:
				self.nil_exempt_non_gst.setdefault(d.parent, [0.0, 0.0, 0.0])
				self.nil_exempt_non_gst[d.parent][2] += d.get("taxable_value", 0)

	def get_items_based_on_tax_rate(self):
		hsn_wise_tax_rate = get_hsn_wise_tax_rates()

		self.tax_details = frappe.db.sql(
			"""
			select
				parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
			from `tab%s`
			where
				parenttype = %s and docstatus = 1
				and parent in (%s)
			order by account_head
		"""
			% (self.tax_doctype, "%s", ", ".join(["%s"] * len(self.invoices.keys()))),
			tuple([self.doctype] + list(self.invoices.keys())),
		)

		self.items_based_on_tax_rate = {}
		self.invoice_cess = frappe._dict()
		self.cgst_sgst_invoices = []

		unidentified_gst_accounts = []
		unidentified_gst_accounts_invoice = []
		for parent, account, item_wise_tax_detail, tax_amount in self.tax_details:
			if account in self.gst_accounts.cess_account:
				self.invoice_cess.setdefault(parent, tax_amount)
			else:
				if item_wise_tax_detail:
					try:
						item_wise_tax_detail = json.loads(item_wise_tax_detail)
						cgst_or_sgst = False
						if account in self.gst_accounts.cgst_account or account in self.gst_accounts.sgst_account:
							cgst_or_sgst = True

						if not (cgst_or_sgst or account in self.gst_accounts.igst_account):
							if "gst" in account.lower() and account not in unidentified_gst_accounts:
								unidentified_gst_accounts.append(account)
								unidentified_gst_accounts_invoice.append(parent)
							continue

						for item_code, tax_amounts in item_wise_tax_detail.items():
							tax_rate = tax_amounts[0]
							if tax_rate:
								if cgst_or_sgst:
									tax_rate *= 2
									if parent not in self.cgst_sgst_invoices:
										self.cgst_sgst_invoices.append(parent)

								rate_based_dict = self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
									tax_rate, []
								)
								if item_code not in rate_based_dict:
									rate_based_dict.append(item_code)
					except ValueError:
						continue
		if unidentified_gst_accounts:
			frappe.msgprint(
				_("Following accounts might be selected in GST Settings:")
				+ "<br>"
				+ "<br>".join(unidentified_gst_accounts),
				alert=True,
			)

		# Build itemised tax for export invoices where tax table is blank (Export and SEZ Invoices)
		for invoice, items in self.invoice_items.items():
			if (
				invoice not in self.items_based_on_tax_rate
				and invoice not in unidentified_gst_accounts_invoice
				and self.invoices.get(invoice, {}).get("export_type") == "Without Payment of Tax"
				and self.invoices.get(invoice, {}).get("gst_category") in ("Overseas", "SEZ")
			):
				self.items_based_on_tax_rate.setdefault(invoice, {})
				for item_code in items.keys():
					hsn_code = self.item_hsn_map.get(item_code)
					tax_rate = 0
					taxable_value = items.get(item_code)
					for rates in hsn_wise_tax_rate.get(hsn_code, []):
						if taxable_value > rates.get("minimum_taxable_value"):
							tax_rate = rates.get("tax_rate")

					self.items_based_on_tax_rate[invoice].setdefault(tax_rate, [])
					self.items_based_on_tax_rate[invoice][tax_rate].append(item_code)

	def get_columns(self):
		self.other_columns = []
		self.tax_columns = []

		if self.filters.get("type_of_business") != "NIL Rated":
			self.tax_columns = [
				{"fieldname": "rate", "label": "Rate", "fieldtype": "Int", "width": 60},
				{
					"fieldname": "taxable_value",
					"label": "Taxable Value",
					"fieldtype": "Currency",
					"width": 100,
				},
			]

		if self.filters.get("type_of_business") == "B2B":
			self.invoice_columns = [
				{
					"fieldname": "billing_address_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150,
				},
				{"fieldname": "customer_name", "label": "Receiver Name", "fieldtype": "Data", "width": 100},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 100,
				},
				{"fieldname": "posting_date", "label": "Invoice date", "fieldtype": "Data", "width": 80},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 100,
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 100,
				},
				{"fieldname": "reverse_charge", "label": "Reverse Charge", "fieldtype": "Data"},
				{"fieldname": "gst_category", "label": "Invoice Type", "fieldtype": "Data"},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 120,
				},
			]
			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100}
			]

		elif self.filters.get("type_of_business") == "B2C Large":
			self.invoice_columns = [
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{"fieldname": "posting_date", "label": "Invoice date", "fieldtype": "Data", "width": 100},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 100,
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120,
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130,
				},
			]
			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100}
			]
		elif self.filters.get("type_of_business") == "CDNR-REG":
			self.invoice_columns = [
				{
					"fieldname": "billing_address_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150,
				},
				{"fieldname": "customer_name", "label": "Receiver Name", "fieldtype": "Data", "width": 120},
				{
					"fieldname": "return_against",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice/Advance Receipt date",
					"fieldtype": "Data",
					"width": 120,
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{"fieldname": "reverse_charge", "label": "Reverse Charge", "fieldtype": "Data"},
				{"fieldname": "export_type", "label": "Export Type", "fieldtype": "Data", "hidden": 1},
				{
					"fieldname": "reason_for_issuing_document",
					"label": "Reason For Issuing document",
					"fieldtype": "Data",
					"width": 140,
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120,
				},
				{"fieldname": "gst_category", "label": "GST Category", "fieldtype": "Data"},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120,
				},
			]
			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100},
				{"fieldname": "pre_gst", "label": "PRE GST", "fieldtype": "Data", "width": 80},
				{"fieldname": "document_type", "label": "Document Type", "fieldtype": "Data", "width": 80},
			]
		elif self.filters.get("type_of_business") == "CDNR-UNREG":
			self.invoice_columns = [
				{"fieldname": "customer_name", "label": "Receiver Name", "fieldtype": "Data", "width": 120},
				{
					"fieldname": "return_against",
					"label": "Issued Against",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{"fieldname": "posting_date", "label": "Note Date", "fieldtype": "Date", "width": 120},
				{
					"fieldname": "invoice_number",
					"label": "Note Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{"fieldname": "export_type", "label": "Export Type", "fieldtype": "Data", "hidden": 1},
				{
					"fieldname": "reason_for_issuing_document",
					"label": "Reason For Issuing document",
					"fieldtype": "Data",
					"width": 140,
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120,
				},
				{"fieldname": "gst_category", "label": "GST Category", "fieldtype": "Data"},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120,
				},
			]
			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100},
				{"fieldname": "pre_gst", "label": "PRE GST", "fieldtype": "Data", "width": 80},
				{"fieldname": "document_type", "label": "Document Type", "fieldtype": "Data", "width": 80},
			]
		elif self.filters.get("type_of_business") == "B2C Small":
			self.invoice_columns = [
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120,
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130,
				},
			]
			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100},
				{"fieldname": "type", "label": "Type", "fieldtype": "Data", "width": 50},
			]
		elif self.filters.get("type_of_business") == "EXPORT":
			self.invoice_columns = [
				{"fieldname": "export_type", "label": "Export Type", "fieldtype": "Data", "width": 120},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120,
				},
				{"fieldname": "posting_date", "label": "Invoice date", "fieldtype": "Data", "width": 120},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120,
				},
				{"fieldname": "port_code", "label": "Port Code", "fieldtype": "Data", "width": 120},
				{
					"fieldname": "shipping_bill_number",
					"label": "Shipping Bill Number",
					"fieldtype": "Data",
					"width": 120,
				},
				{
					"fieldname": "shipping_bill_date",
					"label": "Shipping Bill Date",
					"fieldtype": "Data",
					"width": 120,
				},
			]
		elif self.filters.get("type_of_business") == "Advances":
			self.invoice_columns = [
				{"fieldname": "place_of_supply", "label": "Place Of Supply", "fieldtype": "Data", "width": 120}
			]

			self.other_columns = [
				{"fieldname": "cess_amount", "label": "Cess Amount", "fieldtype": "Currency", "width": 100}
			]
		elif self.filters.get("type_of_business") == "NIL Rated":
			self.invoice_columns = [
				{"fieldname": "description", "label": "Description", "fieldtype": "Data", "width": 420},
				{"fieldname": "nil_rated", "label": "Nil Rated", "fieldtype": "Currency", "width": 200},
				{"fieldname": "exempted", "label": "Exempted", "fieldtype": "Currency", "width": 200},
				{"fieldname": "non_gst", "label": "Non GST", "fieldtype": "Currency", "width": 200},
			]

		self.columns = self.invoice_columns + self.tax_columns + self.other_columns


@frappe.whitelist()
def get_json(filters, report_name, data):
	filters = json.loads(filters)
	report_data = json.loads(data)
	gstin = get_company_gstin_number(filters.get("company"), filters.get("company_address"))

	fp = "%02d%s" % (getdate(filters["to_date"]).month, getdate(filters["to_date"]).year)

	gst_json = {"version": "GST3.0.4", "hash": "hash", "gstin": gstin, "fp": fp}

	res = {}
	if filters["type_of_business"] == "B2B":
		for item in report_data[:-1]:
			res.setdefault(item["billing_address_gstin"], {}).setdefault(item["invoice_number"], []).append(
				item
			)

		out = get_b2b_json(res, gstin)
		gst_json["b2b"] = out

	elif filters["type_of_business"] == "B2C Large":
		for item in report_data[:-1]:
			res.setdefault(item["place_of_supply"], []).append(item)

		out = get_b2cl_json(res, gstin)
		gst_json["b2cl"] = out

	elif filters["type_of_business"] == "B2C Small":
		out = get_b2cs_json(report_data[:-1], gstin)
		gst_json["b2cs"] = out

	elif filters["type_of_business"] == "EXPORT":
		for item in report_data[:-1]:
			res.setdefault(item["export_type"], {}).setdefault(item["invoice_number"], []).append(item)

		out = get_export_json(res)
		gst_json["exp"] = out
	elif filters["type_of_business"] == "CDNR-REG":
		for item in report_data[:-1]:
			res.setdefault(item["billing_address_gstin"], {}).setdefault(item["invoice_number"], []).append(
				item
			)

		out = get_cdnr_reg_json(res, gstin)
		gst_json["cdnr"] = out
	elif filters["type_of_business"] == "CDNR-UNREG":
		for item in report_data[:-1]:
			res.setdefault(item["invoice_number"], []).append(item)

		out = get_cdnr_unreg_json(res, gstin)
		gst_json["cdnur"] = out

	elif filters["type_of_business"] == "Advances":
		for item in report_data[:-1]:
			if not item.get("place_of_supply"):
				frappe.throw(
					_(
						"""{0} not entered in some entries.
					Please update and try again"""
					).format(frappe.bold("Place Of Supply"))
				)

			res.setdefault(item["place_of_supply"], []).append(item)

		out = get_advances_json(res, gstin)
		gst_json["at"] = out

	elif filters["type_of_business"] == "NIL Rated":
		res = report_data[:-1]
		out = get_exempted_json(res)
		gst_json["nil"] = out

	return {"report_name": report_name, "report_type": filters["type_of_business"], "data": gst_json}


def get_b2b_json(res, gstin):
	out = []
	for gst_in in res:
		b2b_item, inv = {"ctin": gst_in, "inv": []}, []
		if not gst_in:
			continue

		for number, invoice in res[gst_in].items():
			if not invoice[0]["place_of_supply"]:
				frappe.throw(
					_(
						"""{0} not entered in Invoice {1}.
					Please update and try again"""
					).format(
						frappe.bold("Place Of Supply"), frappe.bold(invoice[0]["invoice_number"])
					)
				)

			inv_item = get_basic_invoice_detail(invoice[0])
			inv_item["pos"] = "%02d" % int(invoice[0]["place_of_supply"].split("-")[0])
			inv_item["rchrg"] = invoice[0]["reverse_charge"]
			inv_item["inv_typ"] = get_invoice_type(invoice[0])

			if inv_item["pos"] == "00":
				continue
			inv_item["itms"] = []

			for item in invoice:
				inv_item["itms"].append(get_rate_and_tax_details(item, gstin))

			inv.append(inv_item)

		if not inv:
			continue
		b2b_item["inv"] = inv
		out.append(b2b_item)

	return out


def get_b2cs_json(data, gstin):
	company_state_number = gstin[0:2]

	out = []
	for d in data:
		if not d.get("place_of_supply"):
			frappe.throw(
				_(
					"""{0} not entered in some invoices.
				Please update and try again"""
				).format(frappe.bold("Place Of Supply"))
			)

		pos = d.get("place_of_supply").split("-")[0]
		tax_details = {}

		rate = d.get("rate", 0)
		tax = flt((d["taxable_value"] * rate) / 100.0, 2)

		if company_state_number == pos:
			tax_details.update({"camt": flt(tax / 2.0, 2), "samt": flt(tax / 2.0, 2)})
		else:
			tax_details.update({"iamt": tax})

		inv = {
			"sply_ty": "INTRA" if company_state_number == pos else "INTER",
			"pos": pos,
			"typ": d.get("type"),
			"txval": flt(d.get("taxable_value"), 2),
			"rt": rate,
			"iamt": flt(tax_details.get("iamt"), 2),
			"camt": flt(tax_details.get("camt"), 2),
			"samt": flt(tax_details.get("samt"), 2),
			"csamt": flt(d.get("cess_amount"), 2),
		}

		if d.get("type") == "E" and d.get("ecommerce_gstin"):
			inv.update({"etin": d.get("ecommerce_gstin")})

		out.append(inv)

	return out


def get_advances_json(data, gstin):
	company_state_number = gstin[0:2]
	out = []
	for place_of_supply, items in data.items():
		supply_type = "INTRA" if company_state_number == place_of_supply.split("-")[0] else "INTER"
		row = {"pos": place_of_supply.split("-")[0], "itms": [], "sply_ty": supply_type}

		for item in items:
			itms = {
				"rt": item["rate"],
				"ad_amount": flt(item.get("taxable_value")),
				"csamt": flt(item.get("cess_amount")),
			}

			if supply_type == "INTRA":
				itms.update(
					{
						"samt": flt((itms["ad_amount"] * itms["rt"]) / 100),
						"camt": flt((itms["ad_amount"] * itms["rt"]) / 100),
						"rt": itms["rt"] * 2,
					}
				)
			else:
				itms.update({"iamt": flt((itms["ad_amount"] * itms["rt"]) / 100)})

			row["itms"].append(itms)
		out.append(row)

	return out


def get_b2cl_json(res, gstin):
	out = []
	for pos in res:
		if not pos:
			frappe.throw(
				_(
					"""{0} not entered in some invoices.
				Please update and try again"""
				).format(frappe.bold("Place Of Supply"))
			)

		b2cl_item, inv = {"pos": "%02d" % int(pos.split("-")[0]), "inv": []}, []

		for row in res[pos]:
			inv_item = get_basic_invoice_detail(row)
			if row.get("sale_from_bonded_wh"):
				inv_item["inv_typ"] = "CBW"

			inv_item["itms"] = [get_rate_and_tax_details(row, gstin)]

			inv.append(inv_item)

		b2cl_item["inv"] = inv
		out.append(b2cl_item)

	return out


def get_export_json(res):
	out = []
	for exp_type in res:
		exp_item, inv = {"exp_typ": exp_type, "inv": []}, []

		for number, invoice in res[exp_type].items():
			inv_item = get_basic_invoice_detail(invoice[0])
			inv_item["itms"] = []

			for item in invoice:
				inv_item["itms"].append(
					{
						"txval": flt(item["taxable_value"], 2),
						"rt": flt(item["rate"]),
						"iamt": flt((item["taxable_value"] * flt(item["rate"])) / 100.0, 2)
						if exp_type != "WOPAY"
						else 0,
						"csamt": (flt(item.get("cess_amount"), 2) or 0),
					}
				)

			inv.append(inv_item)

		exp_item["inv"] = inv
		out.append(exp_item)

	return out


def get_cdnr_reg_json(res, gstin):
	out = []

	for gst_in in res:
		cdnr_item, inv = {"ctin": gst_in, "nt": []}, []
		if not gst_in:
			continue

		for number, invoice in res[gst_in].items():
			if not invoice[0]["place_of_supply"]:
				frappe.throw(
					_(
						"""{0} not entered in Invoice {1}.
					Please update and try again"""
					).format(
						frappe.bold("Place Of Supply"), frappe.bold(invoice[0]["invoice_number"])
					)
				)

			inv_item = {
				"nt_num": invoice[0]["invoice_number"],
				"nt_dt": getdate(invoice[0]["posting_date"]).strftime("%d-%m-%Y"),
				"val": abs(flt(invoice[0]["invoice_value"])),
				"ntty": invoice[0]["document_type"],
				"pos": "%02d" % int(invoice[0]["place_of_supply"].split("-")[0]),
				"rchrg": invoice[0]["reverse_charge"],
				"inv_typ": get_invoice_type(invoice[0]),
			}

			inv_item["itms"] = []
			for item in invoice:
				inv_item["itms"].append(get_rate_and_tax_details(item, gstin))

			inv.append(inv_item)

		if not inv:
			continue
		cdnr_item["nt"] = inv
		out.append(cdnr_item)

	return out


def get_cdnr_unreg_json(res, gstin):
	out = []

	for invoice, items in res.items():
		inv_item = {
			"nt_num": items[0]["invoice_number"],
			"nt_dt": getdate(items[0]["posting_date"]).strftime("%d-%m-%Y"),
			"val": abs(flt(items[0]["invoice_value"])),
			"ntty": items[0]["document_type"],
			"pos": "%02d" % int(items[0]["place_of_supply"].split("-")[0]),
			"typ": get_invoice_type(items[0]),
		}

		inv_item["itms"] = []
		for item in items:
			inv_item["itms"].append(get_rate_and_tax_details(item, gstin))

		out.append(inv_item)

	return out


def get_exempted_json(data):
	out = {
		"inv": [
			{"sply_ty": "INTRB2B"},
			{"sply_ty": "INTRAB2B"},
			{"sply_ty": "INTRB2C"},
			{"sply_ty": "INTRAB2C"},
		]
	}

	for i, v in enumerate(data):
		if data[i].get("nil_rated"):
			out["inv"][i]["nil_amt"] = data[i]["nil_rated"]

		if data[i].get("exempted"):
			out["inv"][i]["expt_amt"] = data[i]["exempted"]

		if data[i].get("non_gst"):
			out["inv"][i]["ngsup_amt"] = data[i]["non_gst"]

	return out


def get_invoice_type(row):
	gst_category = row.get("gst_category")

	if gst_category == "SEZ":
		return "SEWP" if row.get("export_type") == "WPAY" else "SEWOP"

	if gst_category == "Overseas":
		return "EXPWP" if row.get("export_type") == "WPAY" else "EXPWOP"

	return (
		{
			"Deemed Export": "DE",
			"Registered Regular": "R",
			"Registered Composition": "R",
			"Unregistered": "B2CL",
		}
	).get(gst_category)


def get_basic_invoice_detail(row):
	return {
		"inum": row["invoice_number"],
		"idt": getdate(row["posting_date"]).strftime("%d-%m-%Y"),
		"val": flt(row["invoice_value"], 2),
	}


def get_rate_and_tax_details(row, gstin):
	itm_det = {
		"txval": flt(row["taxable_value"], 2),
		"rt": row["rate"],
		"csamt": (flt(row.get("cess_amount"), 2) or 0),
	}

	# calculate rate
	num = 1 if not row["rate"] else "%d%02d" % (row["rate"], 1)
	rate = row.get("rate") or 0

	# calculate tax amount added
	tax = flt((row["taxable_value"] * rate) / 100.0, 2)
	if row.get("billing_address_gstin") and gstin[0:2] == row["billing_address_gstin"][0:2]:
		itm_det.update({"camt": flt(tax / 2.0, 2), "samt": flt(tax / 2.0, 2)})
	else:
		itm_det.update({"iamt": tax})

	return {"num": int(num), "itm_det": itm_det}


def get_company_gstin_number(company, address=None, all_gstins=False):
	gstin = ""
	if address:
		gstin = frappe.db.get_value("Address", address, "gstin")

	if not gstin:
		filters = [
			["is_your_company_address", "=", 1],
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company],
			["Dynamic Link", "parenttype", "=", "Address"],
			["gstin", "!=", ""],
		]
		gstin = frappe.get_all(
			"Address", filters=filters, pluck="gstin", order_by="is_primary_address desc"
		)
		if gstin and not all_gstins:
			gstin = gstin[0]

	if not gstin:
		address = frappe.bold(address) if address else ""
		frappe.throw(
			_("Please set valid GSTIN No. in Company Address {} for company {}").format(
				address, frappe.bold(company)
			)
		)

	return gstin


@frappe.whitelist()
def download_json_file():
	"""download json content in a file"""
	data = frappe._dict(frappe.local.form_dict)
	frappe.response["filename"] = (
		frappe.scrub("{0} {1}".format(data["report_name"], data["report_type"])) + ".json"
	)
	frappe.response["filecontent"] = data["data"]
	frappe.response["content_type"] = "application/json"
	frappe.response["type"] = "download"


def is_inter_state(invoice_detail):
	if invoice_detail.place_of_supply.split("-")[0] != invoice_detail.company_gstin[:2]:
		return True
	else:
		return False


@frappe.whitelist()
def get_company_gstins(company):
	address = frappe.qb.DocType("Address")
	links = frappe.qb.DocType("Dynamic Link")

	addresses = (
		frappe.qb.from_(address)
		.inner_join(links)
		.on(address.name == links.parent)
		.select(address.gstin)
		.distinct()
		.where(links.link_doctype == "Company")
		.where(links.link_name == company)
		.where(address.gstin.isnotnull())
		.where(address.gstin != "")
		.run(as_dict=1)
	)

	address_list = [""] + [d.gstin for d in addresses]

	return address_list


def get_hsn_wise_tax_rates():
	hsn_wise_tax_rate = {}
	gst_hsn_code = frappe.qb.DocType("GST HSN Code")
	hsn_tax_rates = frappe.qb.DocType("HSN Tax Rate")

	hsn_code_data = (
		frappe.qb.from_(gst_hsn_code)
		.inner_join(hsn_tax_rates)
		.on(gst_hsn_code.name == hsn_tax_rates.parent)
		.select(gst_hsn_code.hsn_code, hsn_tax_rates.tax_rate, hsn_tax_rates.minimum_taxable_value)
		.orderby(hsn_tax_rates.minimum_taxable_value)
		.run(as_dict=1)
	)

	for d in hsn_code_data:
		hsn_wise_tax_rate.setdefault(d.hsn_code, [])
		hsn_wise_tax_rate[d.hsn_code].append(
			{"minimum_taxable_value": d.minimum_taxable_value, "tax_rate": d.tax_rate}
		)

	return hsn_wise_tax_rate
