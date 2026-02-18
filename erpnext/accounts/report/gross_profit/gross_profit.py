# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb, scrub
from frappe.query_builder import Case, Order
from frappe.query_builder.functions import Coalesce
from frappe.utils import cint, flt, formatdate
from pypika.terms import ExistsCriterion

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from erpnext.stock.utils import get_incoming_rate


def execute(filters=None):
	if not filters:
		filters = frappe._dict()
	filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	gross_profit_data = GrossProfitGenerator(filters)

	data = []

	group_wise_columns = frappe._dict(
		{
			"invoice": [
				"invoice_or_item",
				"customer",
				"customer_group",
				"customer_name",
				"posting_date",
				"item_code",
				"item_name",
				"item_group",
				"brand",
				"description",
				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
				"project",
			],
			"item_code": [
				"item_code",
				"item_name",
				"brand",
				"description",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"warehouse": [
				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"brand": [
				"brand",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"item_group": [
				"item_group",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"customer": [
				"customer",
				"customer_group",
				"customer_name",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"customer_group": [
				"customer_group",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"sales_person": [
				"sales_person",
				"allocated_amount",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"project": ["project", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"],
			"cost_center": [
				"cost_center",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"territory": [
				"territory",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"monthly": [
				"monthly",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"payment_term": [
				"payment_term",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
		}
	)

	columns = get_columns(group_wise_columns, filters)

	if filters.group_by == "Invoice":
		get_data_when_grouped_by_invoice(columns, gross_profit_data, filters, group_wise_columns, data)

	else:
		get_data_when_not_grouped_by_invoice(gross_profit_data, filters, group_wise_columns, data)

	return columns, data


def get_data_when_grouped_by_invoice(columns, gross_profit_data, filters, group_wise_columns, data):
	column_names = get_column_names()

	# to display item as Item Code: Item Name
	columns[0]["fieldname"] = "sales_invoice"
	columns[0]["options"] = "Item"
	columns[0]["width"] = 300
	# removing Item Code and Item Name columns
	supplier_master_name = frappe.db.get_single_value("Buying Settings", "supp_master_name")
	customer_master_name = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	if supplier_master_name == "Supplier Name" and customer_master_name == "Customer Name":
		del columns[4:6]
	else:
		del columns[5:7]

	total_base_amount = 0
	total_buying_amount = 0

	for src in gross_profit_data.si_list:
		if src.indent == 1:
			total_base_amount += src.base_amount or 0.0
			total_buying_amount += src.buying_amount or 0.0

		row = frappe._dict()
		row.indent = src.indent
		row.parent_invoice = src.parent_invoice
		row.currency = filters.currency

		for col in group_wise_columns.get(scrub(filters.group_by)):
			row[column_names[col]] = src.get(col)

		data.append(row)

	total_gross_profit = flt(
		total_base_amount + abs(total_buying_amount)
		if total_buying_amount < 0
		else total_base_amount - total_buying_amount,
	)
	data.append(
		frappe._dict(
			{
				"sales_invoice": "Total",
				"qty": None,
				"avg._selling_rate": None,
				"valuation_rate": None,
				"selling_amount": total_base_amount,
				"buying_amount": total_buying_amount,
				"gross_profit": total_gross_profit,
				"gross_profit_%": flt(
					(total_gross_profit / abs(total_base_amount)) * 100.0,
					cint(frappe.db.get_default("currency_precision")) or 3,
				)
				if total_base_amount
				else 0,
			}
		)
	)


def get_data_when_not_grouped_by_invoice(gross_profit_data, filters, group_wise_columns, data):
	total_base_amount = 0
	total_buying_amount = 0

	group_columns = group_wise_columns.get(scrub(filters.group_by))

	# removing customer_name from group columns
	customer_master_name = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	supplier_master_name = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	if "customer_name" in group_columns and (
		supplier_master_name == "Supplier Name" and customer_master_name == "Customer Name"
	):
		group_columns = [col for col in group_columns if col != "customer_name"]

	for src in gross_profit_data.grouped_data:
		total_base_amount += src.base_amount or 0.00
		total_buying_amount += src.buying_amount or 0.00

		row = [src.get(col) for col in group_columns] + [filters.currency]

		data.append(row)

	total_gross_profit = flt(
		total_base_amount + abs(total_buying_amount)
		if total_buying_amount < 0
		else total_base_amount - total_buying_amount,
	)
	currency_precision = cint(frappe.db.get_default("currency_precision")) or 3
	gross_profit_percent = (total_gross_profit / abs(total_base_amount) * 100.0) if total_base_amount else 0

	total_row = {
		group_columns[0]: "Total",
		"base_amount": total_base_amount,
		"buying_amount": total_buying_amount,
		"gross_profit": total_gross_profit,
		"gross_profit_percent": flt(gross_profit_percent, currency_precision),
	}

	total_row = [total_row.get(col, None) for col in [*group_columns, "currency"]]
	data.append(total_row)


def get_columns(group_wise_columns, filters):
	columns = []

	supplier_master_name = frappe.db.get_single_value("Buying Settings", "supp_master_name")
	customer_master_name = frappe.db.get_single_value("Selling Settings", "cust_master_name")

	column_map = frappe._dict(
		{
			"parent": {
				"label": _("Sales Invoice"),
				"fieldname": "parent_invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 120,
			},
			"invoice_or_item": {
				"label": _("Sales Invoice"),
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 120,
			},
			"posting_date": {
				"label": _("Posting Date"),
				"fieldname": "posting_date",
				"fieldtype": "Date",
				"width": 120,
			},
			"posting_time": {
				"label": _("Posting Time"),
				"fieldname": "posting_time",
				"fieldtype": "Data",
				"width": 100,
			},
			"item_code": {
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			"item_name": {
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Data",
				"width": 100,
			},
			"item_group": {
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			"brand": {"label": _("Brand"), "fieldtype": "Link", "options": "Brand", "width": 100},
			"description": {
				"label": _("Description"),
				"fieldname": "description",
				"fieldtype": "Data",
				"width": 100,
			},
			"warehouse": {
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			},
			"qty": {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
			"base_rate": {
				"label": _("Avg. Selling Rate"),
				"fieldname": "avg._selling_rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"buying_rate": {
				"label": _("Valuation Rate"),
				"fieldname": "valuation_rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"base_amount": {
				"label": _("Selling Amount"),
				"fieldname": "selling_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"buying_amount": {
				"label": _("Buying Amount"),
				"fieldname": "buying_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"gross_profit": {
				"label": _("Gross Profit"),
				"fieldname": "gross_profit",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"gross_profit_percent": {
				"label": _("Gross Profit Percent"),
				"fieldname": "gross_profit_%",
				"fieldtype": "Percent",
				"width": 100,
			},
			"project": {
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 140,
			},
			"cost_center": {
				"label": _("Cost Center"),
				"fieldname": "cost_center",
				"fieldtype": "Link",
				"options": "Cost Center",
				"width": 140,
			},
			"sales_person": {
				"label": _("Sales Person"),
				"fieldname": "sales_person",
				"fieldtype": "Link",
				"options": "Sales Person",
				"width": 100,
			},
			"allocated_amount": {
				"label": _("Allocated Amount"),
				"fieldname": "allocated_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"customer": {
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 100,
			},
			"customer_group": {
				"label": _("Customer Group"),
				"fieldname": "customer_group",
				"fieldtype": "Link",
				"options": "Customer Group",
				"width": 100,
			},
			"customer_name": {
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 150,
			},
			"territory": {
				"label": _("Territory"),
				"fieldname": "territory",
				"fieldtype": "Link",
				"options": "Territory",
				"width": 100,
			},
			"monthly": {
				"label": _("Monthly"),
				"fieldname": "monthly",
				"fieldtype": "Data",
				"width": 100,
			},
			"payment_term": {
				"label": _("Payment Term"),
				"fieldname": "payment_term",
				"fieldtype": "Link",
				"options": "Payment Term",
				"width": 170,
			},
		}
	)

	for col in group_wise_columns.get(scrub(filters.group_by)):
		if col == "customer_name" and (
			supplier_master_name == "Supplier Name" and customer_master_name == "Customer Name"
		):
			continue
		columns.append(column_map.get(col))

	columns.append(
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		}
	)

	return columns


def get_column_names():
	return frappe._dict(
		{
			"invoice_or_item": "sales_invoice",
			"customer": "customer",
			"customer_group": "customer_group",
			"customer_name": "customer_name",
			"posting_date": "posting_date",
			"item_code": "item_code",
			"item_name": "item_name",
			"item_group": "item_group",
			"brand": "brand",
			"description": "description",
			"warehouse": "warehouse",
			"qty": "qty",
			"base_rate": "avg._selling_rate",
			"buying_rate": "valuation_rate",
			"base_amount": "selling_amount",
			"buying_amount": "buying_amount",
			"gross_profit": "gross_profit",
			"gross_profit_percent": "gross_profit_%",
			"project": "project",
		}
	)


class GrossProfitGenerator:
	def __init__(self, filters=None):
		self.sle = {}
		self.data = []
		self.average_buying_rate = {}
		self.filters = frappe._dict(filters)
		self.load_invoice_items()
		self.get_delivery_notes()

		self.load_product_bundle()
		if filters.group_by == "Invoice":
			self.group_items_by_invoice()

		self.load_non_stock_items()
		self.get_returned_invoice_items()
		self.process()

	def process(self):
		self.grouped = {}
		self.grouped_data = []

		self.currency_precision = cint(frappe.db.get_default("currency_precision")) or 3
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 2

		grouped_by_invoice = True if self.filters.get("group_by") == "Invoice" else False

		if grouped_by_invoice:
			buying_amount = 0
			base_amount = 0

		for row in reversed(self.si_list):
			if self.filters.get("group_by") == "Monthly":
				row.monthly = formatdate(row.posting_date, "MMM YYYY")

			if self.skip_row(row):
				continue

			row.base_amount = flt(row.base_net_amount, self.currency_precision)

			product_bundles = []
			if row.update_stock:
				product_bundles = self.product_bundles.get(row.parenttype, {}).get(row.parent, frappe._dict())
			elif row.dn_detail:
				product_bundles = self.product_bundles.get("Delivery Note", {}).get(
					row.delivery_note, frappe._dict()
				)
				row.item_row = row.dn_detail
				# Update warehouse and base_amount from 'Packed Item' List
				if product_bundles and not row.parent:
					# For Packed Items, row.parent_invoice will be the Bundle name
					product_bundle = product_bundles.get(row.parent_invoice)
					if product_bundle:
						for packed_item in product_bundle:
							if (
								packed_item.get("item_code") == row.item_code
								and packed_item.get("parent_detail_docname") == row.item_row
							):
								row.warehouse = packed_item.warehouse
								row.base_amount = packed_item.base_amount

			# get buying amount
			if row.item_code in product_bundles:
				row.buying_amount = flt(
					self.get_buying_amount_from_product_bundle(row, product_bundles[row.item_code]),
					self.currency_precision,
				)
			else:
				row.buying_amount = flt(self.get_buying_amount(row, row.item_code), self.currency_precision)

			if grouped_by_invoice and row.indent == 0.0:
				row.buying_amount = buying_amount
				row.base_amount = base_amount
				buying_amount = 0
				base_amount = 0

			# get buying rate
			if flt(row.qty):
				row.buying_rate = flt(row.buying_amount / flt(row.qty), self.float_precision)
				row.base_rate = flt(row.base_amount / flt(row.qty), self.float_precision)
			else:
				if self.is_not_invoice_row(row):
					row.buying_rate, row.base_rate = 0.0, 0.0

			if self.is_not_invoice_row(row):
				self.update_return_invoices(row)

			if grouped_by_invoice and row.indent == 1.0:
				buying_amount += row.buying_amount
				base_amount += row.base_amount

			# calculate gross profit
			row.gross_profit = flt(
				row.base_amount + abs(row.buying_amount)
				if row.buying_amount < 0
				else row.base_amount - row.buying_amount,
				self.currency_precision,
			)
			if row.base_amount:
				row.gross_profit_percent = flt(
					(row.gross_profit / abs(row.base_amount)) * 100.0,
					self.currency_precision,
				)
			else:
				row.gross_profit_percent = 0.0

			# add to grouped
			self.grouped.setdefault(row.get(scrub(self.filters.group_by)), []).append(row)

		if self.grouped:
			self.get_average_rate_based_on_group_by()

	def update_return_invoices(self, row):
		if row.parent in self.returned_invoices and row.item_code in self.returned_invoices[row.parent]:
			returned_item_rows = self.returned_invoices[row.parent][row.item_code]
			for returned_item_row in returned_item_rows:
				# returned_items 'qty' should be stateful
				if returned_item_row.qty != 0:
					if row.qty >= abs(returned_item_row.qty):
						row.qty += returned_item_row.qty
						row.base_amount += flt(returned_item_row.base_amount, self.currency_precision)
						returned_item_row.qty = 0
						returned_item_row.base_amount = 0

					else:
						row.qty = 0
						row.base_amount = 0
						returned_item_row.qty += row.qty
						returned_item_row.base_amount += row.base_amount

			row.buying_amount = flt(flt(row.qty) * flt(row.buying_rate), self.currency_precision)

	def get_average_rate_based_on_group_by(self):
		for key in list(self.grouped):
			if self.filters.get("group_by") == "Payment Term":
				for i, row in enumerate(self.grouped[key]):
					invoice_portion = 0

					if row.is_return:
						invoice_portion = 100
					elif row.invoice_portion:
						invoice_portion = row.invoice_portion
					elif row.payment_amount:
						invoice_portion = row.payment_amount * 100 / row.base_net_amount

					if i == 0:
						new_row = row
						self.set_average_based_on_payment_term_portion(new_row, row, invoice_portion)
					else:
						new_row.qty += flt(row.qty)
						self.set_average_based_on_payment_term_portion(new_row, row, invoice_portion, True)

				new_row = self.set_average_rate(new_row)
				self.grouped_data.append(new_row)
			elif self.filters.get("group_by") != "Invoice":
				for i, row in enumerate(self.grouped[key]):
					if i == 0:
						new_row = row
					else:
						new_row.qty += flt(row.qty)
						new_row.buying_amount += flt(row.buying_amount, self.currency_precision)
						new_row.base_amount += flt(row.base_amount, self.currency_precision)
						if self.filters.get("group_by") == "Sales Person":
							new_row.allocated_amount += flt(row.allocated_amount, self.currency_precision)
				new_row = self.set_average_rate(new_row)
				self.grouped_data.append(new_row)

	def set_average_based_on_payment_term_portion(self, new_row, row, invoice_portion, aggr=False):
		cols = ["base_amount", "buying_amount", "gross_profit"]
		for col in cols:
			if aggr:
				new_row[col] += row[col] * invoice_portion / 100
			else:
				new_row[col] = row[col] * invoice_portion / 100

	def is_not_invoice_row(self, row):
		return (self.filters.get("group_by") == "Invoice" and row.indent != 0.0) or self.filters.get(
			"group_by"
		) != "Invoice"

	def set_average_rate(self, new_row):
		self.set_average_gross_profit(new_row)
		new_row.buying_rate = (
			flt(new_row.buying_amount / new_row.qty, self.float_precision) if new_row.qty else 0
		)
		new_row.base_rate = flt(new_row.base_amount / new_row.qty, self.float_precision) if new_row.qty else 0
		return new_row

	def set_average_gross_profit(self, new_row):
		new_row.gross_profit = flt(
			new_row.base_amount + abs(new_row.buying_amount)
			if new_row.buying_amount < 0
			else new_row.base_amount - new_row.buying_amount,
			self.currency_precision,
		)
		new_row.gross_profit_percent = (
			flt(((new_row.gross_profit / abs(new_row.base_amount)) * 100.0), self.currency_precision)
			if new_row.base_amount
			else 0
		)

	def get_returned_invoice_items(self):
		returned_invoices = frappe.db.sql(
			"""
			select
				si.name, si_item.item_code, si_item.stock_qty as qty, si_item.base_net_amount as base_amount, si.return_against
			from
				`tabSales Invoice` si, `tabSales Invoice Item` si_item
			where
				si.name = si_item.parent
				and si.docstatus = 1
				and si.is_return = 1
				and si.posting_date between %(from_date)s and %(to_date)s
		""",
			{"from_date": self.filters.from_date, "to_date": self.filters.to_date},
			as_dict=1,
		)

		self.returned_invoices = frappe._dict()
		for inv in returned_invoices:
			self.returned_invoices.setdefault(inv.return_against, frappe._dict()).setdefault(
				inv.item_code, []
			).append(inv)

	def skip_row(self, row):
		if self.filters.get("group_by") != "Invoice":
			if not row.get(scrub(self.filters.get("group_by", ""))):
				return True

		return False

	def get_buying_amount_from_product_bundle(self, row, product_bundle):
		buying_amount = 0.0
		for packed_item in product_bundle:
			if packed_item.get("parent_detail_docname") == row.item_row:
				packed_item_row = row.copy()
				packed_item_row.warehouse = packed_item.warehouse
				packed_item_row.qty = packed_item.total_qty * -1
				packed_item_row.serial_and_batch_bundle = packed_item.serial_and_batch_bundle
				buying_amount += self.get_buying_amount(packed_item_row, packed_item.item_code)

		return flt(buying_amount, self.currency_precision)

	def calculate_buying_amount_from_sle(self, row, my_sle, parenttype, parent, item_row, item_code):
		for i, sle in enumerate(my_sle):
			# find the stock valution rate from stock ledger entry
			if (
				sle.voucher_type == parenttype
				and parent == sle.voucher_no
				and sle.voucher_detail_no == item_row
			):
				previous_stock_value = len(my_sle) > i + 1 and flt(my_sle[i + 1].stock_value) or 0.0

				if previous_stock_value:
					return abs(previous_stock_value - flt(sle.stock_value)) * flt(row.qty) / abs(flt(sle.qty))
				else:
					return flt(row.qty) * self.get_average_buying_rate(row, item_code)
		return 0.0

	def get_buying_amount(self, row, item_code):
		# IMP NOTE
		# stock_ledger_entries should already be filtered by item_code and warehouse and
		# sorted by posting_date desc, posting_time desc
		if item_code in self.non_stock_items and (row.project or row.cost_center):
			# Issue 6089-Get last purchasing rate for non-stock item
			item_rate = self.get_last_purchase_rate(item_code, row)
			return flt(row.qty) * item_rate

		else:
			my_sle = self.get_stock_ledger_entries(item_code, row.warehouse)
			if (row.update_stock or row.dn_detail) and my_sle:
				parenttype = row.parenttype
				parent = row.invoice or row.parent

				if row.dn_detail:
					parenttype, parent = "Delivery Note", row.delivery_note

				return self.calculate_buying_amount_from_sle(
					row, my_sle, parenttype, parent, row.item_row, item_code
				)
			elif self.delivery_notes.get((row.parent, row.item_code), None):
				#  check if Invoice has delivery notes
				dn = self.delivery_notes.get((row.parent, row.item_code))
				parenttype, parent, item_row, dn_warehouse = (
					"Delivery Note",
					dn["delivery_note"],
					dn["item_row"],
					dn["warehouse"],
				)
				my_sle = self.get_stock_ledger_entries(item_code, dn_warehouse)
				return self.calculate_buying_amount_from_sle(
					row, my_sle, parenttype, parent, item_row, item_code
				)
			elif row.sales_order and row.so_detail:
				incoming_amount = self.get_buying_amount_from_so_dn(row.sales_order, row.so_detail, item_code)
				if incoming_amount:
					return flt(row.qty) * incoming_amount
			else:
				return flt(row.qty) * self.get_average_buying_rate(row, item_code)

		return flt(row.qty) * self.get_average_buying_rate(row, item_code)

	def get_buying_amount_from_so_dn(self, sales_order, so_detail, item_code):
		from frappe.query_builder.functions import Avg

		delivery_note_item = frappe.qb.DocType("Delivery Note Item")

		query = (
			frappe.qb.from_(delivery_note_item)
			.select(Avg(delivery_note_item.incoming_rate))
			.where(delivery_note_item.docstatus == 1)
			.where(delivery_note_item.item_code == item_code)
			.where(delivery_note_item.against_sales_order == sales_order)
			.where(delivery_note_item.so_detail == so_detail)
			.groupby(delivery_note_item.item_code)
		)

		incoming_amount = query.run()
		return flt(incoming_amount[0][0]) if incoming_amount else 0

	def get_average_buying_rate(self, row, item_code):
		args = row
		key = (item_code, row.warehouse)
		if key not in self.average_buying_rate:
			args.update(
				{
					"voucher_type": row.parenttype,
					"voucher_no": row.parent,
					"allow_zero_valuation": True,
					"company": self.filters.company,
					"item_code": item_code,
				}
			)

			if row.serial_and_batch_bundle:
				args.update({"serial_and_batch_bundle": row.serial_and_batch_bundle})

			average_buying_rate = get_incoming_rate(args)
			self.average_buying_rate[key] = flt(average_buying_rate)

		return self.average_buying_rate[key]

	def get_last_purchase_rate(self, item_code, row):
		purchase_invoice = frappe.qb.DocType("Purchase Invoice")
		purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

		query = (
			frappe.qb.from_(purchase_invoice_item)
			.inner_join(purchase_invoice)
			.on(purchase_invoice.name == purchase_invoice_item.parent)
			.select(
				purchase_invoice_item.base_rate / purchase_invoice_item.conversion_factor,
			)
			.where(purchase_invoice.docstatus == 1)
			.where(purchase_invoice.posting_date <= self.filters.to_date)
			.where(purchase_invoice_item.item_code == item_code)
			.where(purchase_invoice.is_return == 0)
			.where(purchase_invoice_item.parenttype == "Purchase Invoice")
		)

		if row.project:
			query = query.where(purchase_invoice_item.project == row.project)

		if row.cost_center:
			query = query.where(purchase_invoice_item.cost_center == row.cost_center)

		query = query.orderby(purchase_invoice.posting_date, order=frappe.qb.desc).limit(1)
		last_purchase_rate = query.run()

		return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0

	def load_invoice_items(self):
		self.si_list = []

		SalesInvoice = frappe.qb.DocType("Sales Invoice")
		base_query = self.prepare_invoice_query()

		if self.filters.include_returned_invoices:
			invoice_query = base_query.where(
				(SalesInvoice.is_return == 0)
				| ((SalesInvoice.is_return == 1) & SalesInvoice.return_against.isnull())
			)
		else:
			invoice_query = base_query.where(SalesInvoice.is_return == 0)

		self.si_list += invoice_query.run(as_dict=True)
		self.prepare_vouchers_to_ignore()

		ret_invoice_query = base_query.where(
			(SalesInvoice.is_return == 1) & SalesInvoice.return_against.isnotnull()
		)
		if self.vouchers_to_ignore:
			ret_invoice_query = ret_invoice_query.where(
				SalesInvoice.return_against.notin(self.vouchers_to_ignore)
			)

		self.si_list += ret_invoice_query.run(as_dict=True)

	def prepare_invoice_query(self):
		SalesInvoice = frappe.qb.DocType("Sales Invoice")
		SalesInvoiceItem = frappe.qb.DocType("Sales Invoice Item")
		Item = frappe.qb.DocType("Item")
		SalesTeam = frappe.qb.DocType("Sales Team")
		PaymentSchedule = frappe.qb.DocType("Payment Schedule")

		query = (
			frappe.qb.from_(SalesInvoice)
			.join(SalesInvoiceItem)
			.on(SalesInvoiceItem.parent == SalesInvoice.name)
			.join(Item)
			.on(Item.name == SalesInvoiceItem.item_code)
			.where((SalesInvoice.docstatus == 1) & (SalesInvoice.is_opening != "Yes"))
		)

		query = self.apply_common_filters(query, SalesInvoice, SalesInvoiceItem, SalesTeam, Item)

		query = query.select(
			SalesInvoiceItem.parenttype,
			SalesInvoiceItem.parent,
			SalesInvoice.posting_date,
			SalesInvoice.posting_time,
			SalesInvoice.project,
			SalesInvoice.update_stock,
			SalesInvoice.customer,
			SalesInvoice.customer_group,
			SalesInvoice.customer_name,
			SalesInvoice.territory,
			SalesInvoiceItem.item_code,
			SalesInvoice.base_net_total.as_("invoice_base_net_total"),
			SalesInvoiceItem.item_name,
			SalesInvoiceItem.description,
			SalesInvoiceItem.warehouse,
			SalesInvoiceItem.item_group,
			SalesInvoiceItem.brand,
			SalesInvoiceItem.so_detail,
			SalesInvoiceItem.sales_order,
			SalesInvoiceItem.dn_detail,
			SalesInvoiceItem.delivery_note,
			SalesInvoiceItem.stock_qty.as_("qty"),
			SalesInvoiceItem.base_net_rate,
			SalesInvoiceItem.base_net_amount,
			SalesInvoiceItem.name.as_("item_row"),
			SalesInvoice.is_return,
			SalesInvoiceItem.cost_center,
			SalesInvoiceItem.serial_and_batch_bundle,
		)

		if self.filters.group_by == "Sales Person":
			query = query.select(
				SalesTeam.sales_person,
				(SalesTeam.allocated_percentage * SalesInvoiceItem.base_net_amount / 100).as_(
					"allocated_amount"
				),
				SalesTeam.incentives,
			)

			query = query.left_join(SalesTeam).on(SalesTeam.parent == SalesInvoice.name)

		if self.filters.group_by == "Payment Term":
			query = query.select(
				Case()
				.when(SalesInvoice.is_return == 1, _("Sales Return"))
				.else_(Coalesce(PaymentSchedule.payment_term, _("No Terms")))
				.as_("payment_term"),
				PaymentSchedule.invoice_portion,
				PaymentSchedule.payment_amount,
			)

			query = query.left_join(PaymentSchedule).on(
				(PaymentSchedule.parent == SalesInvoice.name) & (SalesInvoice.is_return == 0)
			)

		query = query.orderby(SalesInvoice.posting_date, order=Order.desc).orderby(
			SalesInvoice.posting_time, order=Order.desc
		)

		return query

	def apply_common_filters(self, query, SalesInvoice, SalesInvoiceItem, SalesTeam, Item):
		if self.filters.company:
			query = query.where(SalesInvoice.company == self.filters.company)

		if self.filters.from_date:
			query = query.where(SalesInvoice.posting_date >= self.filters.from_date)

		if self.filters.to_date:
			query = query.where(SalesInvoice.posting_date <= self.filters.to_date)

		if self.filters.item_group:
			query = query.where(get_item_group_condition(self.filters.item_group, Item))

		if self.filters.sales_person:
			query = query.where(
				ExistsCriterion(
					frappe.qb.from_(SalesTeam)
					.select(1)
					.where(
						(SalesTeam.parent == SalesInvoice.name)
						& (SalesTeam.sales_person == self.filters.sales_person)
					)
				)
			)

		if self.filters.sales_invoice:
			query = query.where(SalesInvoice.name == self.filters.sales_invoice)

		if self.filters.item_code:
			query = query.where(SalesInvoiceItem.item_code == self.filters.item_code)

		if self.filters.cost_center:
			self.filters.cost_center = frappe.parse_json(self.filters.get("cost_center"))
			self.filters.cost_center = get_cost_centers_with_children(self.filters.cost_center)
			query = query.where(SalesInvoiceItem.cost_center.isin(self.filters.cost_center))

		if self.filters.project:
			self.filters.project = frappe.parse_json(self.filters.get("project"))
			query = query.where(SalesInvoiceItem.project.isin(self.filters.project))

		for dim in get_accounting_dimensions(as_list=False) or []:
			if self.filters.get(dim.fieldname):
				if frappe.get_cached_value("DocType", dim.document_type, "is_tree"):
					self.filters[dim.fieldname] = get_dimension_with_children(
						dim.document_type, self.filters.get(dim.fieldname)
					)
				query = query.where(SalesInvoiceItem[dim.fieldname].isin(self.filters[dim.fieldname]))

		if self.filters.warehouse:
			lft, rgt = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"])
			WH = frappe.qb.DocType("Warehouse")
			query = query.where(
				SalesInvoiceItem.warehouse.isin(
					frappe.qb.from_(WH).select(WH.name).where((WH.lft >= lft) & (WH.rgt <= rgt))
				)
			)

		return query

	def prepare_vouchers_to_ignore(self):
		self.vouchers_to_ignore = tuple(row["parent"] for row in self.si_list)

	def get_delivery_notes(self):
		self.delivery_notes = frappe._dict({})
		if self.si_list:
			invoices = [x.parent for x in self.si_list]
			dni = qb.DocType("Delivery Note Item")
			delivery_notes = (
				qb.from_(dni)
				.select(
					dni.against_sales_invoice.as_("sales_invoice"),
					dni.item_code,
					dni.warehouse,
					dni.parent.as_("delivery_note"),
					dni.name.as_("item_row"),
				)
				.where((dni.docstatus == 1) & (dni.against_sales_invoice.isin(invoices)))
				.groupby(dni.against_sales_invoice, dni.item_code)
				.orderby(dni.creation, order=Order.desc)
				.run(as_dict=True)
			)

			for entry in delivery_notes:
				self.delivery_notes[(entry.sales_invoice, entry.item_code)] = entry

	def group_items_by_invoice(self):
		"""
		Turns list of Sales Invoice Items to a tree of Sales Invoices with their Items as children.
		"""

		grouped = OrderedDict()
		product_bundles = self.product_bundles.get("Sales Invoice", {})

		for row in self.si_list:
			# initialize list with a header row for each new parent
			grouped.setdefault(row.parent, [self.get_invoice_row(row)]).append(
				row.update(
					{"indent": 1.0, "parent_invoice": row.parent, "invoice_or_item": row.item_code}
				)  # descendant rows will have indent: 1.0 or greater
			)

			# if item is a bundle, add it's components as seperate rows
			if bundled_items := product_bundles.get(row.parent, {}).get(row.item_code):
				for x in bundled_items:
					bundle_item = self.get_bundle_item_row(row, x)
					grouped.get(row.parent).append(bundle_item)

		self.si_list.clear()

		for items in grouped.values():
			self.si_list.extend(items)

	def get_invoice_row(self, row):
		# header row format
		return frappe._dict(
			{
				"parent_invoice": "",
				"indent": 0.0,
				"invoice_or_item": row.parent,
				"parent": None,
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"project": row.project,
				"update_stock": row.update_stock,
				"customer": row.customer,
				"customer_group": row.customer_group,
				"customer_name": row.customer_name,
				"item_code": None,
				"item_name": None,
				"description": None,
				"warehouse": None,
				"item_group": None,
				"brand": None,
				"dn_detail": None,
				"delivery_note": None,
				"qty": None,
				"item_row": None,
				"is_return": row.is_return,
				"cost_center": row.cost_center,
				"base_net_amount": row.invoice_base_net_total,
			}
		)

	def get_bundle_item_row(self, row, item):
		return frappe._dict(
			{
				"parent_invoice": row.item_code,
				"parenttype": row.parenttype,
				"indent": row.indent + 1,
				"parent": None,
				"invoice_or_item": item.item_code,
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"project": row.project,
				"customer": row.customer,
				"customer_group": row.customer_group,
				"customer_name": row.customer_name,
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"warehouse": item.warehouse or row.warehouse,
				"update_stock": row.update_stock,
				"item_group": "",
				"brand": "",
				"dn_detail": row.dn_detail,
				"delivery_note": row.delivery_note,
				"qty": item.total_qty * -1,
				"item_row": row.item_row,
				"is_return": row.is_return,
				"cost_center": row.cost_center,
				"invoice": row.parent,
				"serial_and_batch_bundle": row.serial_and_batch_bundle,
			}
		)

	def get_stock_ledger_entries(self, item_code, warehouse):
		if item_code and warehouse:
			if (item_code, warehouse) not in self.sle:
				sle = qb.DocType("Stock Ledger Entry")
				res = (
					qb.from_(sle)
					.select(
						sle.item_code,
						sle.voucher_type,
						sle.voucher_no,
						sle.voucher_detail_no,
						sle.stock_value,
						sle.warehouse,
						sle.actual_qty.as_("qty"),
					)
					.where(
						(sle.company == self.filters.company)
						& (sle.item_code == item_code)
						& (sle.warehouse == warehouse)
						& (sle.is_cancelled == 0)
					)
					.orderby(sle.item_code)
					.orderby(sle.warehouse, sle.posting_datetime, sle.creation, order=Order.desc)
					.run(as_dict=True)
				)

				self.sle[(item_code, warehouse)] = res

			return self.sle[(item_code, warehouse)]
		return []

	def load_product_bundle(self):
		self.product_bundles = {}

		pki = qb.DocType("Packed Item")

		pki_query = (
			frappe.qb.from_(pki)
			.select(
				pki.parenttype,
				pki.parent,
				pki.parent_item,
				pki.item_code,
				pki.warehouse,
				(-1 * pki.qty).as_("total_qty"),
				pki.rate,
				(pki.rate * pki.qty).as_("base_amount"),
				pki.parent_detail_docname,
				pki.serial_and_batch_bundle,
			)
			.where(pki.docstatus == 1)
		)

		for d in pki_query.run(as_dict=True):
			self.product_bundles.setdefault(d.parenttype, frappe._dict()).setdefault(
				d.parent, frappe._dict()
			).setdefault(d.parent_item, []).append(d)

	def load_non_stock_items(self):
		self.non_stock_items = frappe.db.sql_list(
			"""select name from tabItem
			where is_stock_item=0"""
		)
