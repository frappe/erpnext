# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections.abc import Callable, Iterable
from functools import cached_property

import frappe
from frappe import _
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.utils import DocType
from frappe.utils import get_link_to_form
from frappe.utils.data import add_months, get_first_day


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
		self.fiscal_year = filters.get("fiscal_year")
		self.period_start_month = filters.get("period_start_month")
		self.reporting_period = filters.get("reporting_period")

		self._sales_data = None
		self._purchase_data = None
		self._eu_sales_data = None
		self._eu_purchase_data = None

		# Row IDs
		self.box_row_id = None
		self.rate_row_id = None

		self.box_data = {
			1: [],
			2: [],
			3: [],
			4: [],
			5: [],
			6: [],
			7: [],
			8: [],
			9: [],
		}

		self.box_descriptions = {
			1: "VAT on Sales and All Other Outputs",
			2: "VAT on Purchases from EU (Northern Ireland companies only)",
			3: "Total VAT Due (Box 1 + Box 2)",
			4: "VAT on Purchases",
			5: "Net VAT to be Reclaimed abs(Box 4 - Box 3)",
			6: "Total Value of Sales ex VAT",
			7: "Total Value of Purchases ex VAT",
			8: "EU Goods Sales, ex VAT (Northern Ireland companies only)",
			9: "EU Goods Purchases, ex VAT (Northern Ireland companies only)",
		}

		tax_accumulator = self.get_accumulator("tax_amount")
		net_accumulator = self.get_accumulator("net_amount")
		self.box_calculators = {
			1: tax_accumulator,
			2: tax_accumulator,
			# 3: calculated separately
			4: tax_accumulator,
			# 5: calculated separately
			6: net_accumulator,
			7: net_accumulator,
			8: net_accumulator,
			9: net_accumulator,
		}

	def run(self):
		columns = get_columns()
		data = self.get_data()
		return columns, data

	def get_data(self) -> list[list]:
		"""Return data for the report.

		The report data is a list of rows, with each row being a list of cell values.
		Grouped by VAT Box as required by HMRC Making Tax Digital API.
		"""
		self.calculate_boxes()
		self.box_data[3] = self.calc_box_3()
		self.box_data[5] = self.calc_box_5()

		box_data = []
		for box in sorted(self.box_data.keys()):
			if self.box_data[box]:
				box_data.extend(self.box_data[box])
		return box_data

	@cached_property
	def purchase_data(self):
		"""Get purchase invoice data grouped by tax rate."""
		if self._purchase_data is None:
			self._purchase_data = self.get_purchase_invoice_data()
		return self._purchase_data

	@cached_property
	def sales_data(self):
		"""Get sales invoice data grouped by tax rate."""
		if self._sales_data is None:
			self._sales_data = self.get_sales_invoice_data()
		return self._sales_data

	def filter_tax_rated_data(
		self, data: dict[str | float, list[dict]], key: str, value: str | int
	) -> dict[str | float, list[dict]]:
		"""Filter lists of invoices with <key> by <value>..
		:param data: Dict of tax rate to list of invoice detail rows.
		    { rate: [ {invoice_row}, ... ], ... }
		"""
		return {
			rate: [inv for inv in invs if inv.get(key) == value]
			for rate, invs in data.items()
			if any(inv.get(key) == value for inv in invs)
		}

	@cached_property
	def eu_purchase_data(self):
		"""Get EU purchase invoice data grouped by tax rate."""
		if self._eu_purchase_data is None:
			self._eu_purchase_data = self.filter_tax_rated_data(self.purchase_data, "place_of_supply", "EU")
		return self._eu_purchase_data

	@cached_property
	def eu_sales_data(self):
		"""Get EU sales invoice data grouped by tax rate."""
		if self._eu_sales_data is None:
			self._eu_sales_data = self.filter_tax_rated_data(self.sales_data, "place_of_supply", "EU")
		return self._eu_sales_data

	def calc_box_3(self):
		box_1_value = self.box_data[1][0].get("box_contribution", None)
		if self.box_data[2]:
			box_2_value = self.box_data[2][0].get("box_contribution", None)
		else:
			box_2_value = 0
		if box_1_value is None:  # or box_2_value is None:
			frappe.throw(_("Box 1 and Box 2 must be calculated before Box 3"))
		return [
			{
				"row_head": "Box 3: " + self.box_descriptions[3],
				"box_contribution": box_1_value + box_2_value,
				"party_type": None,
			}
		]

	def calc_box_5(self):
		box_3_value = self.box_data[3][0].get("box_contribution", None)
		box_4_value = self.box_data[4][0].get("box_contribution", None)
		if box_3_value is None or box_4_value is None:
			frappe.throw(_("Box 3 and Box 4 must be calculated before Box 5"))
		return [
			{
				"row_head": "Box 5: " + self.box_descriptions[5],
				"box_contribution": abs(box_4_value - box_3_value),
				"party_type": None,
			}
		]

	def calculate_boxes(self):
		"""Calculate data for each VAT box.
		Iterates through self.box_calculators and populates self.box_data with the result
		of self._format_box_section for each box.
		"""
		for box_id in self.box_calculators:
			data_by_rate = self.get_data_by_rate(box_id)
			self.box_data[box_id] = self._format_box_section(
				box_id=box_id,
				box_description=self.get_box_description(box_id),
				data_by_rate=data_by_rate,
				calculator=self.box_calculators[box_id],
				show_details=True,
			)

	def get_box_description(self, box_id: int) -> str:
		return self.box_descriptions.get(box_id, "Unknown Box")

	def get_data_by_rate(self, box_id: int) -> dict:
		"""Return invoice data grouped by tax rate for the given VAT box."""
		sales_data = self.sales_data
		purchase_data = self.purchase_data
		eu_sales_data = self.eu_sales_data
		eu_purchase_data = self.eu_purchase_data
		self.data_by_rate = {
			1: sales_data,
			2: eu_sales_data,
			3: None,
			4: purchase_data,
			5: None,
			6: sales_data,
			7: purchase_data,
			8: eu_sales_data,
			9: eu_purchase_data,
		}
		return self.data_by_rate.get(box_id, [])

	def _get_invoice_data(self, invoices, doctype):
		"""Get invoice data grouped by tax rate."""
		tax_rated_invoice_items = self.get_items_based_on_tax_rate(doctype, invoices)

		consolidated_data = self.get_consolidated_data(doctype, invoices, tax_rated_invoice_items)
		return consolidated_data

	def get_purchase_invoice_data(self):
		"""Get purchase invoice data grouped by tax rate."""
		invoices = self.get_purchase_invoices()
		return self._get_invoice_data(invoices, "Purchase Invoice")

	def get_sales_invoice_data(self):
		"""Get sales invoice data grouped by tax rate."""
		invoices = self.get_sales_invoices()
		return self._get_invoice_data(invoices, "Sales Invoice")

	def _format_box_section(
		self,
		box_id,
		box_description,
		data_by_rate,
		calculator: Callable[[Iterable, Iterable | None], float],
		show_details=True,
	):
		"""Format a VAT box section with its invoices grouped by rate.
		:param box_number: The VAT box number (e.g., "Box 1")
		:param box_description: Description of the VAT box
		:param data_by_rate: Dict of tax rate to list of invoice detail rows
		:param show_details: Whether to show individual invoice details or just totals
		:param calculator: Callback function to calculate contributing amount on
		                                   each Invoice Item. `calculator` should accept an
		                                   Iterable of Iterables. return a float
		                                   amount for contribution.

		Call signature of `calculator` should resemble:-
		        def calculator(invoice_items: Iterable[Iterable], output_list: List = None) -> float:
		                '''output_list, if given, will have each Iterable appended to it'''
		                return float
		"""
		box_row_id = f"box_{box_id}"

		# Add box header
		box_header = {
			"row_head": f"Box {box_id}: {_(box_description)}",
			"row_id": box_row_id,
			"parent_row_id": None,
			"indent": 0,
		}

		section_data = [box_header]

		# Calculate totals across all rates
		box_total = 0

		# Add data for each rate
		for rate in sorted(data_by_rate.keys()):
			details = data_by_rate[rate]
			rate_row_id = f"{box_row_id}::rate_{rate}"
			subsection_data = []

			# Calculate rate totals and optionally show invoice details
			box_contribution = calculator(details, subsection_data if show_details else None)

			# Add rate subtotal
			rate_subheader = {
				"row_head": f"Rate: {rate}%",
				"row_id": rate_row_id,
				"parent_row_id": box_row_id,
				"indent": 1,
				"box_contribution": box_contribution,
			}
			section_data.append(rate_subheader)

			# Add row_id, parent_row_id, indent to each detail row
			self.update_invoice_item_row_ids(subsection_data, rate_row_id)

			section_data.extend(subsection_data)

			box_total += box_contribution

		# Update box header with total
		section_data[0].update({"box_contribution": box_total})
		return section_data

	def update_invoice_item_row_ids(self, data: list[dict], rate_row_id: str):
		"""Add row_id and parent_row_id to each row in data.
		:param data: List of invoice/item rows
		:param rate_row_id: The row_id of the parent rate row.
		"""
		for row in data:
			dt = row.get("doctype") or ""
			invoice_row_id = f"{rate_row_id}::{row.get('name')}"
			if "Item" in dt:
				item_code = row.get("item_code")
				item_row_id = f"{invoice_row_id}::{item_code}"
				item_label = f"{item_code}: {row.get('item_name')}"
				item_link = get_link_to_form(dt, item_code, label=item_label)
				row.update(
					{
						"row_head": item_link,
						"row_id": item_row_id,
						"parent_row_id": invoice_row_id,
						"indent": 3,
					}
				)
			elif "Invoice" in dt:
				row.update(
					{
						"row_head": row.get("name"),
						"row_id": invoice_row_id,
						"parent_row_id": rate_row_id,
						"indent": 2,
					}
				)
		return

	def get_accumulator(self, amount_field: str) -> Callable[[Iterable, Iterable | None], float]:
		"""Return an accumulator function for the specified amount field.

		Args:
		        amount_field: The field to accumulate (e.g., "tax_amount", "net_amount")

		Returns:
		        A function that accumulates the specified `amount_field` from
		        invoice details.  The function expects an Iterable of invoice detail
		        dicts and an optional output list to which the invoices will be
		        appended.
		"""

		def accumulator(data: Iterable, output_list: Iterable | None = None) -> float:
			total = 0.0
			for row in data:
				box_contribution = row.get(amount_field, 0)
				if output_list is not None:
					# Do not modify the original row dict
					out = row | {"box_contribution": box_contribution}
					output_list.append(out)
				if row.get("is_summary_row"):
					continue
				total += box_contribution
			return total

		return accumulator

	def get_consolidated_data(self, doctype, invoices, items_based_on_tax_rate):
		"""Here we want to arrange the data hierarchically>-
		1. Group by tax rate
		2. List invoices under each tax rate
		3. List Items in each Invoice at that tax rate.
		"""
		consolidated_data_map = {}
		if doctype == "Sales Invoice":
			item_doctype = "Sales Invoice Item"
			party_type = "Customer"
		else:
			item_doctype = "Purchase Invoice Item"
			party_type = "Supplier"
		invoices_dict = {inv.name: inv for inv in invoices}
		for rate, rate_invoices in items_based_on_tax_rate.items():
			for invoice_id, items in rate_invoices.items():
				invoice = invoices_dict.get(invoice_id)
				# Must have an invoice here.
				if not invoice:
					continue
				place_of_supply = self.get_place_of_supply(invoice)
				consolidated_data_map.setdefault(rate, [])
				if invoice.name not in items_based_on_tax_rate[rate]:
					continue

				invoice_data = [
					{
						"name": invoice_id,
						"account": invoice.get("account"),
						"posting_date": invoice.get(
							"posting_date"
						),  # formatdate(invoice.get("posting_date"), "dd-mm-yyyy"),
						"doctype": doctype,
						"party_type": party_type,
						"party": invoice.get("party"),
						"remarks": invoice.get("remarks"),
						"tax_category": invoice.get("invoice_tax_category", ""),
						"place_of_supply": place_of_supply,
					}
				]

				invoice_amounts = {
					"tax_amount": 0,
					"net_amount": 0,
					"gross_amount": 0,
				}
				# for item in items_based_on_tax_rate[rate][invoice.name]:
				for item in items:
					tax_amount = item.get("amount")
					net_amount = item.get("taxable_amount")
					gross_amount = tax_amount + net_amount
					item_tax_template = item.get("item_tax_template")
					category = self.get_item_category(invoice, item)
					item.update(
						{
							"doctype": item_doctype,
							"tax_amount": tax_amount,
							"gross_amount": gross_amount,
							"net_amount": net_amount,
							"item_category": category,
							"item_tax_template": item_tax_template,
						}
					)
					invoice_data.append(item)

					# Accumulate totals for the invoice
					invoice_amounts["tax_amount"] += tax_amount
					invoice_amounts["net_amount"] += net_amount
					invoice_amounts["gross_amount"] += gross_amount

				invoice_amounts["is_summary_row"] = True
				invoice_data[0].update(invoice_amounts)
				consolidated_data_map[rate].extend(invoice_data)

		return consolidated_data_map

	def get_items_based_on_tax_rate(self, doctype, invoices):
		from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import (
			get_tax_details_query,
		)

		if doctype == "Sales Invoice":
			tax_doctype = "Sales Taxes and Charges"
			item_doctype = "Sales Invoice Item"
		else:
			tax_doctype = "Purchase Taxes and Charges"
			item_doctype = "Purchase Invoice Item"

		items_based_on_tax_rate = frappe._dict()
		if not invoices:
			return items_based_on_tax_rate
		invoice_names = [_.name for _ in invoices]

		item_wise_tax = frappe.qb.DocType("Item Wise Tax Detail")
		invoice_item = frappe.qb.DocType(item_doctype)
		taxes_and_charges = frappe.qb.DocType(tax_doctype)

		vat_accounts = self.get_vat_accounts()
		self.validate_vat_accounts(vat_accounts)
		vat_account_names = [acc["name"] for acc in vat_accounts]

		tax_details_query = (
			get_tax_details_query(doctype, tax_doctype)
			.left_join(invoice_item)
			.on(invoice_item.name == item_wise_tax.item_row)
			.select(
				invoice_item.item_code,
				invoice_item.item_name,
				invoice_item.item_tax_template,
			)
			.where(item_wise_tax.parent.isin(invoice_names))
			.where(taxes_and_charges.account_head.isin(vat_account_names))
			.orderby(item_wise_tax.parent, invoice_item.idx)
		)
		tax_details = tax_details_query.run(as_dict=True)

		for row in tax_details:
			invoice = row.parent
			rate = row.rate
			items_based_on_tax_rate.setdefault(rate, {}).setdefault(invoice, []).append(row)
		return items_based_on_tax_rate

	def get_purchase_invoices_query(self):
		Invoice = DocType("Purchase Invoice")
		Address = DocType("Address")
		shipping_address = Address.as_("shipping_address")
		dispatch_address = Address.as_("dispatch_address")
		supplier_address = Address.as_("supplier_address")
		invoice_query = (
			frappe.qb.from_(Invoice)
			.select(
				ConstantColumn("Purchase Invoice").as_("doctype"),
				ConstantColumn("Supplier").as_("party_type"),
				Invoice.name.as_("name"),
				Invoice.supplier.as_("party"),
				Invoice.posting_date.as_("posting_date"),
				Invoice.grand_total.as_("net_amount"),
				Invoice.total_taxes_and_charges.as_("tax_amount"),
				Invoice.tax_category.as_("invoice_tax_category"),
				Invoice.shipping_address.as_("shipping_address"),
				Invoice.dispatch_address.as_("dispatch_address"),
				shipping_address.tax_category.as_("shipping_tax_category"),
				shipping_address.country.as_("shipping_country"),
				dispatch_address.tax_category.as_("dispatch_tax_category"),
				dispatch_address.country.as_("dispatch_country"),
				supplier_address.tax_category.as_("supplier_tax_category"),
				supplier_address.country.as_("supplier_country"),
			)
			.left_join(shipping_address)
			.on(Invoice.shipping_address == shipping_address.name)
			.left_join(dispatch_address)
			.on(Invoice.dispatch_address == dispatch_address.name)
			.left_join(supplier_address)
			.on(Invoice.supplier_address == supplier_address.name)
			.where(Invoice.docstatus == 1)
			.where(Invoice.company == self.company)
		)
		return self.filter_date_range(invoice_query, Invoice)

	def get_sales_invoices_query(self):
		Invoice = DocType("Sales Invoice")
		Address = DocType("Address")
		shipping_address = Address.as_("shipping_address")
		branch_address = Address.as_("company_address")
		invoice_query = (
			frappe.qb.from_(Invoice)
			.select(
				ConstantColumn("Sales Invoice").as_("doctype"),
				ConstantColumn("Customer").as_("party_type"),
				Invoice.name.as_("name"),
				Invoice.customer.as_("party"),
				Invoice.posting_date.as_("posting_date"),
				Invoice.grand_total.as_("net_amount"),
				Invoice.total_taxes_and_charges.as_("tax_amount"),
				Invoice.tax_category.as_("invoice_tax_category"),
				Invoice.shipping_address_name.as_("shipping_address"),
				Invoice.company_address.as_("company_address"),
				shipping_address.country.as_("shipping_country"),
				shipping_address.tax_category.as_("shipping_tax_category"),
				branch_address.country.as_("company_country"),
				branch_address.tax_category.as_("company_tax_category"),
			)
			.left_join(shipping_address)
			.on(Invoice.shipping_address == shipping_address.name)
			.left_join(branch_address)
			.on(Invoice.company_address == branch_address.name)
			.where(Invoice.docstatus == 1)
			.where(Invoice.company == self.company)
		)
		return self.filter_date_range(invoice_query, Invoice)

	def filter_date_range(self, query, dt):
		"""Filter the query by the reporting period, start year and month."""
		from datetime import datetime

		n_months = {
			_("Annually"): 12,
			_("Quarterly"): 3,
			_("Bi-Monthly"): 2,
			_("Monthly"): 1,
		}.get(self.reporting_period, 3)  # Default to Quarterly

		start_month = self.period_start_month
		fiscal_year = self.fiscal_year
		_date = datetime.strptime(f"{fiscal_year} {start_month}", "%Y %B")
		start_date = get_first_day(_date)

		if start_date:
			from_date = start_date.strftime("%Y-%m-%d")
			to_date = add_months(start_date, n_months).strftime("%Y-%m-%d")
			date_filter = dt.posting_date[from_date:to_date]
			query = query.where(date_filter)
		return query

	def get_sales_invoices(self):
		invoice_query = self.get_sales_invoices_query()
		invoices = invoice_query.run(as_dict=True)
		return invoices

	def get_purchase_invoices(self):
		invoice_query = self.get_purchase_invoices_query()
		invoices = invoice_query.run(as_dict=True)
		return invoices

	def get_place_of_supply(self, invoice_data):
		"""Determine place of supply based on tax category and address.

		Logic from README:
		1. Check if Invoice has tax category for EU/ROTW export
		2. Check Address objects in the following order:
		   a. Shipping Address
		   b. Dispatch Address (Purchases only)
		   c. Supplier Address (Purchases only)
		   d. Company Address
		3. Default to United Kingdom

		Returns: "UK", "EU", "ROTW", or "Outside Scope"
		"""

		def _check_category(tax_category):
			if tax_category == "VAT - EU Address":
				return "EU"
			elif tax_category == "VAT - Rest of World Address":
				return "ROTW"
			elif tax_category == "VAT - Outside Scope":
				return "Outside Scope"
			return None

		for tax_category_field in [
			"invoice_tax_category",
			"shipping_tax_category",
			"dispatch_tax_category",
			"supplier_tax_category",
			"company_tax_category",
		]:
			tax_category = invoice_data.get(tax_category_field)
			if tax_region := _check_category(tax_category):
				return tax_region

		# Everything else should default to UK
		return "UK"

	def get_item_category(self, invoice_data, item_data):
		"""Determine if item is Goods or Services based on tax category.

		In ERPNext's design:
		- The invoice has a tax_category field that can be set to "Goods" or "Services"
		- This tax_category is used as a filter when selecting item_tax_templates
		- Items have a taxes child table where rows can specify which item_tax_template
		  to use for a given tax_category

		For UK VAT purposes, we primarily use the invoice's tax_category.
		If not specified, we default to "Goods" as per UK README.md.

		Returns: "Goods" or "Services"
		"""
		# Use invoice-level tax category - this is set explicitly by the user
		invoice_tax_category = invoice_data.get("tax_category", "")
		if "Goods" in invoice_tax_category:
			return "Goods"
		elif "Services" in invoice_tax_category:
			return "Services"

		# Default to Goods for UK VAT (as per UK README.md)
		return "Goods"

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
		return vat_accounts

	def validate_vat_accounts(self, vat_accounts):
		accounts = {}
		for acc in vat_accounts:
			acc_type = acc.pop("root_type")
			accounts.setdefault(acc_type, []).append(acc.copy())

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
			"label": _("Row DocType"),
			"fieldname": "doctype",
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
			"label": _("HMRC Box / Rate / Invoice"),
			"fieldname": "row_head",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 120,
		},
		{
			"fieldname": "tax_category",
			"label": _("Invoice Tax Category"),
			"fieldtype": "Link",
			"options": "Tax Category",
			"width": 100,
		},
		{"fieldname": "place_of_supply", "label": _("Place of Supply"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "item_tax_template",
			"label": _("Item Tax Template"),
			"fieldtype": "Link",
			"options": "Item Tax Template",
			"width": 100,
		},
		{"fieldname": "box_contribution", "label": "Contribution", "fieldtype": "Currency", "width": 130},
	]
