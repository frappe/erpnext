# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	gross_profit_data = GrossProfitGenerator(filters)

	data = []
	source = gross_profit_data.grouped_data if filters.get("group_by") != "Invoice" else gross_profit_data.data

	group_wise_columns = frappe._dict({
		"invoice": ["parent", "customer", "posting_date", "posting_time", "item_code", "item_name", "brand", "description", \
			"warehouse", "qty", "base_rate", "buying_rate", "base_amount",
			"buying_amount", "gross_profit", "gross_profit_percent", "project"],
		"item_code": ["item_code", "item_name", "brand", "description", "warehouse", "qty", "base_rate",
			"buying_rate", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"],
		"warehouse": ["warehouse", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"territory": ["territory", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"brand": ["brand", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"item_group": ["item_group", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"customer": ["customer", "customer_group", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"customer_group": ["customer_group", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"sales_person": ["sales_person", "allocated_amount", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
			"gross_profit", "gross_profit_percent"],
		"project": ["project", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"],
		"territory": ["territory", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"]
	})

	columns = get_columns(group_wise_columns, filters)

	for src in source:
		row = []
		for col in group_wise_columns.get(scrub(filters.group_by)):
			row.append(src.get(col))
		data.append(row)

	return columns, data

def get_columns(group_wise_columns, filters):
	columns = []
	column_map = frappe._dict({
		"parent": _("Sales Invoice") + ":Link/Sales Invoice:120",
		"posting_date": _("Posting Date") + ":Date",
		"posting_time": _("Posting Time"),
		"item_code": _("Item Code") + ":Link/Item",
		"item_name": _("Item Name"),
		"item_group": _("Item Group") + ":Link/Item",
		"brand": _("Brand"),
		"description": _("Description"),
		"warehouse": _("Warehouse") + ":Link/Warehouse",
		"qty": _("Qty") + ":Float",
		"base_rate": _("Avg. Selling Rate") + ":Currency",
		"buying_rate": _("Avg. Buying Rate") + ":Currency",
		"base_amount": _("Selling Amount") + ":Currency",
		"buying_amount": _("Buying Amount") + ":Currency",
		"gross_profit": _("Gross Profit") + ":Currency",
		"gross_profit_percent": _("Gross Profit %") + ":Percent",
		"project": _("Project") + ":Link/Project",
		"sales_person": _("Sales person"),
		"allocated_amount": _("Allocated Amount") + ":Currency",
		"customer": _("Customer") + ":Link/Customer",
		"customer_group": _("Customer Group") + ":Link/Customer Group",
		"territory": _("Territory") + ":Link/Territory"
	})

	for col in group_wise_columns.get(scrub(filters.group_by)):
		columns.append(column_map.get(col))

	return columns

class GrossProfitGenerator(object):
	def __init__(self, filters=None):
		self.data = []
		self.average_buying_rate = {}
		self.filters = frappe._dict(filters)
		self.load_invoice_items()
		self.load_stock_ledger_entries()
		self.load_product_bundle()
		self.load_non_stock_items()
		self.process()

	def process(self):
		self.grouped = {}
		for row in self.si_list:
			if self.skip_row(row, self.product_bundles):
				continue

			row.base_amount = flt(row.base_net_amount)

			if row.update_stock:
				product_bundles = self.product_bundles.get(row.parenttype, {}).get(row.parent, frappe._dict())
			elif row.dn_detail:
				product_bundles = self.product_bundles.get("Delivery Note", {})\
					.get(row.delivery_note, frappe._dict())
				row.item_row = row.dn_detail
			
			# get buying amount
			if row.item_code in product_bundles:
				row.buying_amount = self.get_buying_amount_from_product_bundle(row, 
					product_bundles[row.item_code])
			else:
				row.buying_amount = self.get_buying_amount(row, row.item_code)

			# get buying rate
			if row.qty:
				row.buying_rate = row.buying_amount / row.qty
				row.base_rate = row.base_amount / row.qty
			else:
				row.buying_rate, row.base_rate = 0.0, 0.0

			# calculate gross profit
			row.gross_profit = row.base_amount - row.buying_amount
			if row.base_amount:
				row.gross_profit_percent = (row.gross_profit / row.base_amount) * 100.0
			else:
				row.gross_profit_percent = 0.0

			# add to grouped
			if self.filters.group_by != "Invoice":
				self.grouped.setdefault(row.get(scrub(self.filters.group_by)), []).append(row)

			self.data.append(row)

		if self.grouped:
			self.collapse_group()
		else:
			self.grouped_data = []

	def collapse_group(self):
		# sum buying / selling totals for group
		self.grouped_data = []
		for key in self.grouped.keys():
			for i, row in enumerate(self.grouped[key]):
				if i==0:
					new_row = row
				else:
					new_row.qty += row.qty
					new_row.buying_amount += row.buying_amount
					new_row.base_amount += row.base_amount

			new_row.gross_profit = new_row.base_amount - new_row.buying_amount
			new_row.gross_profit_percent = ((new_row.gross_profit / new_row.base_amount) * 100.0) \
				if new_row.base_amount else 0
			new_row.buying_rate = (new_row.buying_amount / new_row.qty) \
				if new_row.qty else 0

			self.grouped_data.append(new_row)

	def skip_row(self, row, product_bundles):
		if self.filters.get("group_by") != "Invoice" and not row.get(scrub(self.filters.get("group_by"))):
			return True

	def get_buying_amount_from_product_bundle(self, row, product_bundle):
		buying_amount = 0.0
		for packed_item in product_bundle:
			if packed_item.get("parent_detail_docname")==row.item_row:
				buying_amount += self.get_buying_amount(row, packed_item.item_code)

		return buying_amount

	def get_buying_amount(self, row, item_code):
		# IMP NOTE
		# stock_ledger_entries should already be filtered by item_code and warehouse and
		# sorted by posting_date desc, posting_time desc
		if item_code in self.non_stock_items:
			# average purchasing rate for non-stock items
			item_rate = self.get_average_buying_rate(item_code)
			return flt(row.qty) * item_rate

		else:
			my_sle = self.sle.get((item_code, row.warehouse))
			if (row.update_stock or row.dn_detail) and my_sle:
				parenttype, parent = row.parenttype, row.parent
				if row.dn_detail:
					parenttype, parent = "Delivery Note", row.delivery_note
				
				for i, sle in enumerate(my_sle):
					# find the stock valution rate from stock ledger entry
					if sle.voucher_type == parenttype and parent == sle.voucher_no and \
						sle.voucher_detail_no == row.item_row:
							previous_stock_value = len(my_sle) > i+1 and \
								flt(my_sle[i+1].stock_value) or 0.0
							return  previous_stock_value - flt(sle.stock_value)
			else:
				return flt(row.qty) * self.get_average_buying_rate(item_code)


		return 0.0

	def get_average_buying_rate(self, item_code):
		if not item_code in self.average_buying_rate:
			if item_code in self.non_stock_items:
				self.average_buying_rate[item_code] = flt(frappe.db.sql("""select sum(base_net_amount) / sum(qty)
					from `tabPurchase Invoice Item`
					where item_code = %s and docstatus=1""", item_code)[0][0])
			else:
				self.average_buying_rate[item_code] = flt(frappe.db.sql("""select avg(valuation_rate)
					from `tabStock Ledger Entry`
					where item_code = %s and ifnull(qty_after_transaction,0) > 0""", item_code)[0][0])

		return self.average_buying_rate[item_code]

	def load_invoice_items(self):
		conditions = ""
		if self.filters.company:
			conditions += " and company = %(company)s"
		if self.filters.from_date:
			conditions += " and posting_date >= %(from_date)s"
		if self.filters.to_date:
			conditions += " and posting_date <= %(to_date)s"

		self.si_list = frappe.db.sql("""select item.parenttype, item.parent,
				si.posting_date, si.posting_time, si.project_name, si.update_stock,
				si.customer, si.customer_group, si.territory,
				item.item_code, item.item_name, item.description, item.warehouse,
				item.item_group, item.brand, item.dn_detail, item.delivery_note,
				item.qty, item.base_net_rate, item.base_net_amount, item.name as "item_row",
				sales.sales_person, sales.allocated_amount, sales.incentives
			from `tabSales Invoice` si
			inner join `tabSales Invoice Item` item on item.parent = si.name
			left join `tabSales Team` sales on sales.parent = si.name
			where
				si.docstatus = 1 and si.is_return != 1 %s
			order by
				si.posting_date desc, si.posting_time desc""" % (conditions,), self.filters, as_dict=1)

	def load_stock_ledger_entries(self):
		res = frappe.db.sql("""select item_code, voucher_type, voucher_no,
				voucher_detail_no, stock_value, warehouse, actual_qty as qty
			from `tabStock Ledger Entry`
			where company=%(company)s
			order by
				item_code desc, warehouse desc, posting_date desc,
				posting_time desc, name desc""", self.filters, as_dict=True)
		self.sle = {}
		for r in res:
			if (r.item_code, r.warehouse) not in self.sle:
				self.sle[(r.item_code, r.warehouse)] = []

			self.sle[(r.item_code, r.warehouse)].append(r)

	def load_product_bundle(self):
		self.product_bundles = {}

		for d in frappe.db.sql("""select parenttype, parent, parent_item,
			item_code, warehouse, -1*qty as total_qty, parent_detail_docname
			from `tabPacked Item` where docstatus=1""", as_dict=True):
			self.product_bundles.setdefault(d.parenttype, frappe._dict()).setdefault(d.parent,
				frappe._dict()).setdefault(d.parent_item, []).append(d)

	def load_non_stock_items(self):
		self.non_stock_items = frappe.db.sql_list("""select name from tabItem
			where is_stock_item=0""")
