# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_link_to_form

from erpnext import get_region
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
		if not self.sa_vat_accounts and not frappe.in_test and not frappe.flags.in_migrate:
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
		item_doctype = frappe.qb.DocType(doctype + " Item")
		items = (
			frappe.qb.from_(item_doctype)
			.select(item_doctype.name, item_doctype.is_zero_rated, item_doctype.base_net_amount)
			.where(item_doctype.parent.isin(list(self.invoices.keys())))
			.run(as_dict=True)
		)
		self.invoice_items = frappe._dict({item.name: item for item in items})

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
			.select(item_wise_tax.tax_row)
			.where(item_wise_tax.parent.isin(invoice_names))
			.where(taxes_and_charges.account_head.isin(self.sa_vat_accounts))
		)
		if doctype == "Purchase Invoice":
			tax_details = tax_details.select(taxes_and_charges.add_deduct_tax)
		tax_details = tax_details.run(as_dict=True)
		actual_tax_rates = get_actual_tax_rates(tax_details)

		for row in tax_details:
			is_zero_rated = self.invoice_items.get(row.item_row, {}).get("is_zero_rated")
			if row.charge_type == "Actual":
				row.rate = actual_tax_rates.get(row.tax_row, 0)
			if row.rate == 0 and not is_zero_rated:
				continue

			self.add_item_tax(row)

	def add_item_tax(self, row: dict) -> None:
		"""Add input (Add) and output (Deduct) VAT separately, counting each item's taxable amount once."""
		is_deduct = row.add_deduct_tax == "Deduct"
		totals = self.items_based_on_tax_rate.setdefault(row.parent, {}).setdefault(
			(row.rate, is_deduct),
			{"gross_amount": 0.0, "tax_amount": 0.0, "net_amount": 0.0, "items": set()},
		)
		net_amount = 0.0
		if row.item_row not in totals["items"]:
			totals["items"].add(row.item_row)
			net_amount = self.get_deducted_net_amount(row) if is_deduct else row.taxable_amount

		totals["tax_amount"] += row.amount
		totals["net_amount"] += net_amount
		totals["gross_amount"] += row.amount + net_amount

	def get_deducted_net_amount(self, row: dict) -> float:
		"""Deduct rows store the taxable amount negated, or as is when migrated, so use the item line's sign."""
		item_net_amount = flt(self.invoice_items.get(row.item_row, {}).get("base_net_amount"))
		sign = -1 if item_net_amount < 0 else 1
		return abs(flt(row.taxable_amount)) * sign

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

			for (rate, _is_deduct), item_details in rate_details.items():
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


def get_actual_tax_rates(tax_details: list[dict]) -> dict[str, float]:
	"""Rate of each Actual tax row on its whole taxable amount, so its items aren't split by rounding."""
	totals = {}
	for row in tax_details:
		if row.charge_type == "Actual":
			amount, taxable_amount = totals.get(row.tax_row, (0.0, 0.0))
			totals[row.tax_row] = (amount + flt(row.amount), taxable_amount + flt(row.taxable_amount))

	return {
		tax_row: flt(amount / taxable_amount * 100, 2)
		for tax_row, (amount, taxable_amount) in totals.items()
		if taxable_amount
	}
