# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

class GrossProfitGenerator(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters)
		self.load_invoice_items()
		self.load_stock_ledger_entries()
		self.load_sales_bom()
		self.load_non_stock_items()
		self.process(filters.group_by)

	def process(self, group_by):
		self.grouped = {}
		for row in self.data:
			row.selling_amount = flt(row.base_amount)

			sales_boms = self.sales_boms.get(row.parenttype, {}).get(row.name, frappe._dict())

			# get buying amount
			if row.item_code in sales_boms:
				row.buying_amount = self.get_buying_amount_from_sales_bom(row, sales_boms[row.item_code])
			else:
				row.buying_amount = self.get_buying_amount(row, row.item_code)

			# calculate gross profit
			row.gross_profit = row.buying_amount - row.selling_amount
			if row.selling_amount:
				row.gross_profit_percent = (row.gross_profit / row.selling_amount) * 100.0
			else:
				row.gross_profit_percent = 0.0

			print row ####
			# add to grouped
			# if self.filters.group_by:
			# 	self.grouped.setdefault(self.filters.group_by, []).append(row.get(self.filters.group_by))
			if group_by:
				self.grouped.setdefault(self.filters.group_by, []).append(row.get(self.filters.group_by))

		if self.grouped:
			return self.collapse_group()
		else:
			return None

		# TODO: append totals

	def collapse_group(self):
		# sum buying / selling totals for group
		self.grouped_data = []
		for key in self.grouped:
			for i, row in enumerate(self.grouped[key]):
				if i==0:
					new_row = row
					self.grouped_data.append(row)
				else:
					print ">>> NEWROW >>>", self.grouped[key] ####
					new_row.buying_amount += row.buying_amount
					new_row.selling_amount += row.selling_amount

			new_row.gross_profit = new_row.selling_amount - new_row.buying_amount
			new_row.gross_profit_percent = ((new_row.gross_profit / new_row.selling_amount) * 100.0) \
				if new_row.selling_amount else 0

		return self.grouped_data

	def get_buying_amount_from_sales_bom(self, row, sales_bom):
		buying_amount = 0.0
		for bom_item in sales_bom[row.item_code]:
			if bom_item.get("parent_detail_docname")==row.name:
				buying_amount += self.get_buying_amount(row, bom_item.item_code)

		return buying_amount

	def get_buying_amount(self, row, item_code):
		# IMP NOTE
		# stock_ledger_entries should already be filtered by item_code and warehouse and
		# sorted by posting_date desc, posting_time desc
		if item_code in self.non_stock_items:
			# average purchasing rate for non-stock items
			item_rate = frappe.db.sql("""select sum(base_amount) / sum(qty)
				from `tabPurchase Invoice Item`
				where item_code = %s and docstatus=1""", item_code)
			return flt(row.qty) * (flt(item_rate[0][0]) if item_rate else 0)

		else:
			# is warehouse copied from DN??
			my_sle = self.sle.get((item_code, row.warehouse))
			for i, sle in enumerate(my_sle):
				# find the stock valution rate from stock ledger entry
				if sle.voucher_type == row.parenttype and row.parent == sle.voucher_no and \
					sle.voucher_detail_no == row.name:
						previous_stock_value = len(my_sle) > i+1 and \
							flt(my_sle[i+1].stock_value) or 0.0
						return  previous_stock_value - flt(sle.stock_value)

		return 0.0

	def load_invoice_items(self):
		conditions = ""
		if self.filters.company:
			conditions += " and company = %(company)s"
		if self.filters.from_date:
			conditions += " and posting_date >= %(from_date)s"
		if self.filters.to_date:
			conditions += " and posting_date <= %(to_date)s"

		self.data = frappe.db.sql("""select item.parenttype, si.name,
				si.posting_date, si.posting_time, si.project_name,
				si.customer, si.customer_group, si.territory,
				item.item_code, item.item_name, item.description, item.warehouse,
				item.item_group, item.brand,
				item.qty, item.base_rate, item.base_amount, item.name as "item_row",
				timestamp(si.posting_date, si.posting_time) as posting_datetime
			from `tabSales Invoice` si, `tabSales Invoice Item` item
			where
				item.parent = si.name and si.docstatus = 1 %s
			order by
				si.posting_date desc, si.posting_time desc""" % (conditions,), self.filters, as_dict=1)

	def load_stock_ledger_entries(self):
		res = frappe.db.sql("""select item_code, voucher_type, voucher_no,
				voucher_detail_no, posting_date, posting_time, stock_value,
				warehouse, actual_qty as qty
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

	def load_sales_bom(self):
		self.sales_boms = {}

		for d in frappe.db.sql("""select parenttype, parent, parent_item,
			item_code, warehouse, -1*qty as total_qty, parent_detail_docname
			from `tabPacked Item` where docstatus=1""", as_dict=True):
			self.sales_boms.setdefault(d.parenttype, frappe._dict()).setdefault(d.parent,
				frappe._dict()).setdefault(d.parent_item, []).append(d)

	def load_non_stock_items(self):
		self.non_stock_items = frappe.db.sql_list("""select name from tabItem
			where is_stock_item='No'""")
