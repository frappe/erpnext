# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, NullIf
from frappe.utils import flt, formatdate, get_link_to_form

from erpnext import get_region


def execute(filters=None):
	return VATAuditReport(filters).run()


class VATAuditReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctypes = ["Purchase Invoice", "Sales Invoice"]

	def run(self):
		self.validate_company_region()
		if self.filters.company:
			frappe.has_permission("Company", doc=self.filters.company, throw=True)
		self.get_sa_vat_accounts()
		self.get_columns()
		for doctype in self.doctypes:
			self.get_invoice_data(doctype)

			if self.invoices:
				self.get_invoice_items(doctype)
				self.get_items_based_on_tax_rate(doctype)
				self.get_data(doctype)

		return self.columns, self.data

	def validate_company_region(self):
		if self.filters.company and get_region(self.filters.company) != "South Africa":
			frappe.throw(
				_(
					"The company {0} is not in South Africa. VAT Audit Report is only available for companies in South Africa."
				).format(frappe.bold(self.filters.company))
			)

	def get_sa_vat_accounts(self):
		self.sa_vat_accounts = frappe.get_all(
			"South Africa VAT Account", filters={"parent": self.filters.company}, pluck="account"
		)
		if not self.sa_vat_accounts and not frappe.flags.in_test and not frappe.flags.in_migrate:
			link_to_settings = get_link_to_form(
				"South Africa VAT Settings", "", label="South Africa VAT Settings"
			)
			frappe.throw(_("Please set VAT Accounts in {0}").format(link_to_settings))

	def get_invoice_data(self, doctype):
		self.invoices = frappe._dict()
		party_field = "supplier" if doctype == "Purchase Invoice" else "customer"
		account_field = "credit_to" if doctype == "Purchase Invoice" else "debit_to"

		invoice_data = frappe.get_list(
			doctype,
			filters=self.get_invoice_filters(),
			fields=[
				"name as voucher_no",
				"posting_date",
				"remarks",
				f"{party_field} as party",
				f"{account_field} as account",
			],
			order_by="posting_date desc",
			limit_page_length=0,
		)

		for row in invoice_data:
			self.invoices.setdefault(row.voucher_no, row)

	def get_invoice_filters(self):
		filters = [["docstatus", "=", 1], ["is_opening", "=", "No"]]
		if self.filters.get("company"):
			filters.append(["company", "=", self.filters.company])
		if self.filters.get("from_date"):
			filters.append(["posting_date", ">=", self.filters.from_date])
		if self.filters.get("to_date"):
			filters.append(["posting_date", "<=", self.filters.to_date])
		return filters

	def get_invoice_items(self, doctype):
		self.invoice_items = frappe._dict()
		item_doctype = frappe.qb.DocType(doctype + " Item")

		items = (
			frappe.qb.from_(item_doctype)
			.select(
				Coalesce(NullIf(item_doctype.item_code, ""), item_doctype.item_name).as_("item"),
				item_doctype.parent,
				item_doctype.base_net_amount,
				item_doctype.is_zero_rated,
			)
			.where(item_doctype.parent.isin(list(self.invoices.keys())))
			.run(as_dict=True)
		)

		for row in items:
			self.invoice_items.setdefault(row.parent, {}).setdefault(row.item, {"net_amount": 0.0})
			self.invoice_items[row.parent][row.item]["net_amount"] += row.get("base_net_amount", 0)
			self.invoice_items[row.parent][row.item]["is_zero_rated"] = row.is_zero_rated

	def get_items_based_on_tax_rate(self, doctype):
		self.items_based_on_tax_rate = frappe._dict()
		self.tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)

		tax_doctype = frappe.qb.DocType(self.tax_doctype)
		query = (
			frappe.qb.from_(tax_doctype)
			.select(
				tax_doctype.parent,
				tax_doctype.account_head,
				tax_doctype.charge_type,
				tax_doctype.item_wise_tax_detail,
			)
			.where(tax_doctype.parenttype == doctype)
			.where(tax_doctype.docstatus == 1)
			.where(tax_doctype.parent.isin(list(self.invoices.keys())))
			.where(tax_doctype.account_head.isin(self.sa_vat_accounts))
			.orderby(tax_doctype.account_head)
		)
		if doctype == "Purchase Invoice":
			query = query.select(tax_doctype.add_deduct_tax)
		self.tax_details = query.run(as_dict=True)

		for tax_detail in self.tax_details:
			if not tax_detail.item_wise_tax_detail:
				continue

			try:
				item_wise_tax_detail = json.loads(tax_detail.item_wise_tax_detail)
			except ValueError:
				continue

			parent_items = self.invoice_items.get(tax_detail.parent, {})
			is_actual = tax_detail.charge_type == "Actual"
			actual_tax_rate = get_actual_tax_rate(item_wise_tax_detail, parent_items) if is_actual else 0

			for item, taxes in item_wise_tax_detail.items():
				is_zero_rated = parent_items.get(item, {}).get("is_zero_rated")
				if is_actual:
					# Actual rows store a rate of 0, so use the rate derived from the row's total
					taxes = [actual_tax_rate, taxes[1]]
				# to skip items with non-zero tax rate in multiple rows
				if taxes[0] == 0 and not is_zero_rated:
					continue

				if item in parent_items:
					self.add_item_tax(tax_detail, item, taxes)

	def add_item_tax(self, tax_detail: dict, item: str, taxes: list) -> None:
		"""Add input (Add) and output (Deduct) VAT separately, counting each item's net amount once."""
		is_deduct = tax_detail.get("add_deduct_tax") == "Deduct"
		totals = self.items_based_on_tax_rate.setdefault(tax_detail.parent, {}).setdefault(
			(taxes[0], is_deduct),
			{"gross_amount": 0.0, "tax_amount": 0.0, "net_amount": 0.0, "items": set()},
		)
		net_amount = 0.0
		if item not in totals["items"]:
			totals["items"].add(item)
			net_amount = flt(self.invoice_items[tax_detail.parent][item].get("net_amount"))

		# item_wise_tax_detail keeps a Deduct row's share with the sign of the item, not of the row
		tax_amount = -flt(taxes[1]) if is_deduct else flt(taxes[1])
		totals["tax_amount"] += tax_amount
		totals["net_amount"] += net_amount
		totals["gross_amount"] += tax_amount + net_amount

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
			for (rate, _is_deduct), item_details in self.items_based_on_tax_rate.get(inv, {}).items():
				row = {
					"account": inv_data.get("account"),
					"posting_date": formatdate(inv_data.get("posting_date"), "dd-mm-yyyy"),
					"voucher_type": doctype,
					"voucher_no": inv,
					"party_type": "Customer" if doctype == "Sales Invoice" else "Supplier",
					"party": inv_data.get("party"),
					"remarks": inv_data.get("remarks"),
					"gross_amount": item_details.get("gross_amount"),
					"tax_amount": item_details.get("tax_amount"),
					"net_amount": item_details.get("net_amount"),
				}

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


def get_actual_tax_rate(item_wise_tax_detail: dict, items: dict) -> float:
	"""Rate of an Actual tax row on its whole taxable amount, so its items aren't split by rounding."""
	tax_amount = sum(flt(taxes[1]) for taxes in item_wise_tax_detail.values())
	taxable_amount = sum(flt(items.get(item, {}).get("net_amount")) for item in item_wise_tax_detail)
	if not taxable_amount:
		return 0
	return flt(tax_amount / taxable_amount * 100, 2)
