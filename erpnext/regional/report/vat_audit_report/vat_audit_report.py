# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.utils import formatdate, get_link_to_form

from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import get_tax_details_query


def execute(filters=None):
	return VATAuditReport(filters).run()


class VATAuditReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctypes = ["Purchase Invoice", "Sales Invoice"]

	def run(self):
		self.get_sa_vat_accounts()
		self.get_columns()
		for doctype in self.doctypes:
			self.select_columns = """
			name as voucher_no,
			posting_date, remarks"""
			columns = (
				", supplier as party, credit_to as account"
				if doctype == "Purchase Invoice"
				else ", customer as party, debit_to as account"
			)
			self.select_columns += columns

			self.get_invoice_data(doctype)

			if self.invoices:
				self.get_invoice_items(doctype)
				self.get_items_based_on_tax_rate(doctype)
				self.get_data(doctype)

		return self.columns, self.data

	def get_sa_vat_accounts(self):
		self.sa_vat_accounts = frappe.get_all(
			"South Africa VAT Account", filters={"parent": self.filters.company}, pluck="account"
		)
		if not self.sa_vat_accounts and not frappe.in_test and not frappe.flags.in_migrate:
			link_to_settings = get_link_to_form(
				"South Africa VAT Settings", "", label="South Africa VAT Settings"
			)
			frappe.throw(_("Please set VAT Accounts in {0}").format(link_to_settings))

	def get_invoice_data(self, doctype):
		conditions = self.get_conditions()
		self.invoices = frappe._dict()

		invoice_data = frappe.db.sql(
			f"""
			SELECT
				{self.select_columns}
			FROM
				`tab{doctype}`
			WHERE
				docstatus = 1 {conditions}
				and is_opening = 'No'
			ORDER BY
				posting_date DESC
			""",
			self.filters,
			as_dict=1,
		)

		for d in invoice_data:
			self.invoices.setdefault(d.voucher_no, d)

	def get_invoice_items(self, doctype):
		self.invoice_items = frappe._dict()
		item_doctype = frappe.qb.DocType(doctype + " Item")
		self.invoice_items = frappe._dict(
			frappe.qb.from_(item_doctype)
			.select(
				item_doctype.name,
				item_doctype.is_zero_rated,
			)
			.where(item_doctype.parent.isin(list(self.invoices.keys())))
			.run(as_list=1)
		)

	def get_items_based_on_tax_rate(self, doctype):
		self.items_based_on_tax_rate = frappe._dict()
		self.tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)

		taxes_and_charges = frappe.qb.DocType(self.tax_doctype)
		item_wise_tax = frappe.qb.DocType("Item Wise Tax Detail")
		invoice_names = list(self.invoices.keys())
		if not invoice_names:
			return

		tax_details = (
			get_tax_details_query(doctype, self.tax_doctype)
			.where(item_wise_tax.parent.isin(invoice_names))
			.where(taxes_and_charges.account_head.isin(self.sa_vat_accounts))
			.run(as_dict=True)
		)

		for row in tax_details:
			parent = row.parent
			item = row.item_row
			is_zero_rated = self.invoice_items.get(item)
			if row.rate == 0 and not is_zero_rated:
				continue

			self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
				row.rate,
				{
					"gross_amount": 0.0,
					"tax_amount": 0.0,
					"net_amount": 0.0,
				},
			)
			self.items_based_on_tax_rate[parent][row.rate]["tax_amount"] += row.amount
			self.items_based_on_tax_rate[parent][row.rate]["net_amount"] += row.taxable_amount
			self.items_based_on_tax_rate[parent][row.rate]["gross_amount"] += row.amount + row.taxable_amount

	def get_conditions(self):
		conditions = ""
		for opts in (
			("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]

		return conditions

	def get_data(self, doctype):
		consolidated_data = self.get_consolidated_data(doctype)
		section_name = _("Purchases") if doctype == "Purchase Invoice" else _("Sales")

		for rate, section in consolidated_data.items():
			rate = int(rate)
			label = frappe.bold(section_name + "- " + "Rate" + " " + str(rate) + "%")
			section_head = {"posting_date": label}
			total_gross = total_tax = total_net = 0
			self.data.append(section_head)
			for row in section.get("data"):
				self.data.append(row)
				total_gross += row["gross_amount"]
				total_tax += row["tax_amount"]
				total_net += row["net_amount"]

			total = {
				"posting_date": frappe.bold(_("Total")),
				"gross_amount": total_gross,
				"tax_amount": total_tax,
				"net_amount": total_net,
				"bold": 1,
			}
			self.data.append(total)
			self.data.append({})

	def get_consolidated_data(self, doctype):
		consolidated_data_map = {}
		for inv, inv_data in self.invoices.items():
			rate_details = self.items_based_on_tax_rate.get(inv, {})
			if not rate_details:
				continue

			for rate, item_details in rate_details.items():
				row = {
					"tax_amount": 0.0,
					"gross_amount": 0.0,
					"net_amount": 0.0,
				}

				row["account"] = inv_data.get("account")
				row["posting_date"] = formatdate(inv_data.get("posting_date"), "dd-mm-yyyy")
				row["voucher_type"] = doctype
				row["voucher_no"] = inv
				row["party_type"] = "Customer" if doctype == "Sales Invoice" else "Supplier"
				row["party"] = inv_data.get("party")
				row["remarks"] = inv_data.get("remarks")
				row["gross_amount"] += item_details.get("gross_amount")
				row["tax_amount"] += item_details.get("tax_amount")
				row["net_amount"] += item_details.get("net_amount")

				consolidated_data_map.setdefault(rate, {"data": []})
				consolidated_data_map[rate]["data"].append(row)

		return consolidated_data_map

	def get_columns(self):
		self.columns = [
			{"fieldname": "posting_date", "label": "Posting Date", "fieldtype": "Data", "width": 200},
			{
				"fieldname": "account",
				"label": "Account",
				"fieldtype": "Link",
				"options": "Account",
				"width": 150,
			},
			{
				"fieldname": "voucher_type",
				"label": "Voucher Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1,
			},
			{
				"fieldname": "voucher_no",
				"label": "Reference",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 150,
			},
			{
				"fieldname": "party_type",
				"label": "Party Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1,
			},
			{
				"fieldname": "party",
				"label": "Party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 150,
			},
			{"fieldname": "remarks", "label": "Details", "fieldtype": "Data", "width": 150},
			{"fieldname": "net_amount", "label": "Net Amount", "fieldtype": "Currency", "width": 130},
			{"fieldname": "tax_amount", "label": "Tax Amount", "fieldtype": "Currency", "width": 130},
			{"fieldname": "gross_amount", "label": "Gross Amount", "fieldtype": "Currency", "width": 130},
		]
