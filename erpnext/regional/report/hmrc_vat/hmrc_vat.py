# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import cached_property

import frappe
from frappe import _
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.utils import DocType
from frappe.types import DF
from frappe.utils import formatdate, get_link_to_form


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	vat_report = UKVatReport(filters)
	return vat_report.run()


class UKVatReport:
	def __init__(self, filters=None):
		self.company = filters.get("company")
		self.from_date = filters.get("from_date")
		self.to_date = filters.get("to_date")

	def run(self):
		columns = get_columns()
		data = self.get_data()
		return columns, data

	def get_data(self) -> list[list]:
		"""Return data for the report.

		The report data is a list of rows, with each row being a list of cell values.
		"""
		data = []
		vat_accounts = self.get_vat_accounts()
		vat_account_names = [vat_accounts[acc]["name"] for acc in vat_accounts]
		doctype_party = [("Sales Invoice", "Customer"), ("Purchase Invoice", "Supplier")]
		for doctype, party in doctype_party:
			invoices = self.get_invoices(doctype, party)
			invoice_items = self.get_invoice_items(doctype, invoices)
			grouped_invoice_items = self.get_items_based_on_tax_rate(doctype, invoices, vat_account_names)

			invoice_item_data = self._get_data(doctype, invoices, invoice_items, grouped_invoice_items)

			data.extend(invoice_item_data)
		return data

	def _get_data(self, doctype, invoices, invoice_items, items_based_on_tax_rate=None):
		consolidated_data = self.get_consolidated_data(
			doctype, invoices, invoice_items, items_based_on_tax_rate
		)

		data = []
		for __, details in consolidated_data.items():
			for row in details["data"]:
				data.append(
					[
						row.get("invoice_type"),
						row.get("party_type"),
						row.get("voucher_no"),
						row.get("party"),
						row.get("posting_date"),
						row.get("gross_amount"),
						row.get("tax_amount"),
					]
				)
		return data

	def get_consolidated_data(self, doctype, invoices, invoice_items, items_based_on_tax_rate):
		consolidated_data_map = {}
		for inv_data in invoices:
			inv = inv_data.get("invoice")
			rate_details = items_based_on_tax_rate.get(inv, {})
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

	def get_items_based_on_tax_rate(self, doctype, invoices, tax_accounts):
		from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import (
			get_tax_details_query,
		)

		tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)
		invoice_names = [_.invoice for _ in invoices]
		if not invoice_names:
			return

		item_wise_tax = frappe.qb.DocType("Item Wise Tax Detail")
		taxes_and_charges = frappe.qb.DocType(tax_doctype)

		tax_details = (
			get_tax_details_query(doctype, tax_doctype)
			.where(item_wise_tax.parent.isin(invoice_names))
			.where(taxes_and_charges.account_head.isin(tax_accounts))
			.run(as_dict=True)
		)

		items_based_on_tax_rate = frappe._dict()
		for row in tax_details:
			parent = row.parent
			items_based_on_tax_rate.setdefault(parent, {}).setdefault(
				row.rate,
				{
					"gross_amount": 0.0,
					"tax_amount": 0.0,
					"net_amount": 0.0,
				},
			)
			items_based_on_tax_rate[parent][row.rate]["tax_amount"] += row.amount
			items_based_on_tax_rate[parent][row.rate]["net_amount"] += row.taxable_amount
			items_based_on_tax_rate[parent][row.rate]["gross_amount"] += row.amount + row.taxable_amount
		return items_based_on_tax_rate

	def get_invoices(
		self,
		invoice_type: DF.Literal["Sales Invoice", "Purchase Invoice"],
		party_type: DF.Literal["Customer", "Supplier"],
	) -> list[dict]:
		dt = DocType(invoice_type)

		invoice_query = (
			frappe.qb.from_(dt)
			.select(
				ConstantColumn(invoice_type).as_("invoice_type"),
				ConstantColumn(party_type).as_("party_type"),
				dt.name.as_("invoice"),
				getattr(dt, party_type.lower()).as_("party"),
				dt.posting_date.as_("posting_date"),
				dt.grand_total.as_("invoice_amount"),
				dt.total_taxes_and_charges.as_("tax_total"),
			)
			.where(dt.docstatus == 1)
			.where(dt.company == self.company)
		)

		if self.from_date or self.to_date:
			from_date = self.from_date or formatdate("0001-01-01")
			to_date = self.to_date or formatdate("9999-12-31")
			date_filter = dt.posting_date[from_date:to_date]
			invoice_query = invoice_query.where(date_filter)
		invoices = invoice_query.run(as_dict=True)
		return invoices

	def get_invoice_items(
		self, invoice_type: DF.Literal["Sales Invoice", "Purchase Invoice"], invoices: list[dict]
	):
		Item = DocType(invoice_type + " Item")
		invoices = [_.invoice for _ in invoices]
		if not invoices:
			return []
		q = (
			frappe.qb.from_(Item)
			.select(
				Item.item_code,
				Item.parent.as_("invoice"),
				Item.base_net_amount.as_("item_amount"),
				Item.item_tax_template.as_("item_tax_template"),
			)
			.where(Item.parent.isin(invoices))
		)
		print(q)
		invoice_items = q.run(as_dict=True)
		return invoice_items

	def get_vat_accounts(self):
		vat_accounts = frappe.get_list(
			"Account",
			fields=["name", "account_type", "tax_type", "root_type"],
			filters=[
				["account_type", "Tax"],
				["is_group", 0],
				["company", self.company],
				["name", "like", "%VAT%"],
			],
		)

		accounts = {}
		for acc in vat_accounts:
			acc_type = acc.pop("root_type")
			accounts[acc_type] = acc.copy()

		if (
			not vat_accounts
			and not frappe.in_test
			and not frappe.flags.in_migrate
			or (not accounts.get("Asset", None) or not accounts.get("Liability", None))
		):
			link_to_company = get_link_to_form("Company", self.company, label="Company Settings")
			frappe.throw(
				_(
					"Please select Manage -> Create Tax Template"
					" (to make one Asset and one Liability Tax Account, for VAT), in {0}"
				).format(link_to_company)
			)
		return accounts


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{
			"label": _("Invoice Type"),
			"fieldname": "invoice_type",
			"fieldtype": "Link",
			"options": "DocType",
			"hidden": True,
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Link",
			"options": "DocType",
			"hidden": True,
		},
		{
			"label": _("Invoice"),
			"fieldname": "invoice",
			"fieldtype": "Dynamic Link",
			"options": "invoice_type",
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 80},
		{
			"label": _("Invoice Amount"),
			"fieldname": "invoice_amount",
			"fieldtype": "Currency",
		},
		{
			"label": _("Tax Total"),
			"fieldname": "tax_total",
			"fieldtype": "Currency",
		},
	]
