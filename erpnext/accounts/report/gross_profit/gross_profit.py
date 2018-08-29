# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from erpnext.stock.utils import get_incoming_rate
from erpnext.controllers.queries import get_match_cond
from frappe.utils import flt


def execute(filters=None):
	if not filters: filters = frappe._dict()
	filters.currency = frappe.get_cached_value('Company',  filters.company,  "default_currency")

	gross_profit_data = GrossProfitGenerator(filters)

	data = []

	group_wise_columns = frappe._dict({
		"invoice": ["parent", "customer", "customer_group", "posting_date","item_code", "item_name","item_group", "brand", "description", \
			"warehouse", "qty", "base_rate", "buying_rate", "base_amount",
			"buying_amount", "gross_profit", "gross_profit_percent", "project"],
		"item_code": ["item_code", "item_name", "brand", "description", "qty", "base_rate",
			"buying_rate", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"],
		"warehouse": ["warehouse", "qty", "base_rate", "buying_rate", "base_amount", "buying_amount",
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

	for src in gross_profit_data.grouped_data:
		row = []
		for col in group_wise_columns.get(scrub(filters.group_by)):
			row.append(src.get(col))

		row.append(filters.currency)
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
		"item_group": _("Item Group") + ":Link/Item Group",
		"brand": _("Brand"),
		"description": _("Description"),
		"warehouse": _("Warehouse") + ":Link/Warehouse",
		"qty": _("Qty") + ":Float",
		"base_rate": _("Avg. Selling Rate") + ":Currency/currency",
		"buying_rate": _("Avg. Buying Rate") + ":Currency/currency",
		"base_amount": _("Selling Amount") + ":Currency/currency",
		"buying_amount": _("Buying Amount") + ":Currency/currency",
		"gross_profit": _("Gross Profit") + ":Currency/currency",
		"gross_profit_percent": _("Gross Profit %") + ":Percent",
		"project": _("Project") + ":Link/Project",
		"sales_person": _("Sales person"),
		"allocated_amount": _("Allocated Amount") + ":Currency/currency",
		"customer": _("Customer") + ":Link/Customer",
		"customer_group": _("Customer Group") + ":Link/Customer Group",
		"territory": _("Territory") + ":Link/Territory"
	})

	for col in group_wise_columns.get(scrub(filters.group_by)):
		columns.append(column_map.get(col))

	columns.append({
		"fieldname": "currency",
		"label" : _("Currency"),
		"fieldtype": "Link",
		"options": "Currency"
	})

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
		self.get_returned_invoice_items()
		self.process()

	def process(self):
		self.grouped = {}
		self.grouped_data = []

		for row in self.si_list:
			if self.skip_row(row, self.product_bundles):
				continue

			row.base_amount = flt(row.base_net_amount)

			product_bundles = []
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
			self.grouped.setdefault(row.get(scrub(self.filters.group_by)), []).append(row)

		if self.grouped:
			self.get_average_rate_based_on_group_by()

	def get_average_rate_based_on_group_by(self):
		# sum buying / selling totals for group
		for key in list(self.grouped):
			if self.filters.get("group_by") != "Invoice":
				for i, row in enumerate(self.grouped[key]):
					if i==0:
						new_row = row
					else:
						new_row.qty += row.qty
						new_row.buying_amount += row.buying_amount
						new_row.base_amount += row.base_amount
				new_row = self.set_average_rate(new_row)
				self.grouped_data.append(new_row)
			else:
				for i, row in enumerate(self.grouped[key]):
					if row.parent in self.returned_invoices \
							and row.item_code in self.returned_invoices[row.parent]:
						returned_item_rows = self.returned_invoices[row.parent][row.item_code]
						for returned_item_row in returned_item_rows:
							row.qty += returned_item_row.qty
							row.base_amount += returned_item_row.base_amount
						row.buying_amount = row.qty * row.buying_rate
					if row.qty or row.base_amount:
						row = self.set_average_rate(row)
						self.grouped_data.append(row)

	def set_average_rate(self, new_row):
		new_row.gross_profit = new_row.base_amount - new_row.buying_amount
		new_row.gross_profit_percent = ((new_row.gross_profit / new_row.base_amount) * 100.0) \
			if new_row.base_amount else 0
		new_row.buying_rate = (new_row.buying_amount / new_row.qty) if new_row.qty else 0
		new_row.base_rate = (new_row.base_amount / new_row.qty) if new_row.qty else 0
		return new_row

	def get_returned_invoice_items(self):
		returned_invoices = frappe.db.sql("""
			select
				si.name, si_item.item_code, si_item.qty, si_item.base_amount, si.return_against
			from
				`tabSales Invoice` si, `tabSales Invoice Item` si_item
			where
				si.name = si_item.parent
				and si.docstatus = 1
				and si.is_return = 1
		""", as_dict=1)

		self.returned_invoices = frappe._dict()
		for inv in returned_invoices:
			self.returned_invoices.setdefault(inv.return_against, frappe._dict())\
				.setdefault(inv.item_code, []).append(inv)

	def skip_row(self, row, product_bundles):
		if self.filters.get("group_by") != "Invoice":
			if not row.get(scrub(self.filters.get("group_by"))):
				return True
		elif row.get("is_return") == 1:
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
			#Issue 6089-Get last purchasing rate for non-stock item
			item_rate = self.get_last_purchase_rate(item_code)
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
							if previous_stock_value:
								return previous_stock_value - flt(sle.stock_value)
							else:
								return flt(row.qty) * self.get_average_buying_rate(row, item_code)
			else:
				return flt(row.qty) * self.get_average_buying_rate(row, item_code)

		return 0.0

	def get_average_buying_rate(self, row, item_code):
		args = row
		if not item_code in self.average_buying_rate:
			if item_code in self.non_stock_items:
				self.average_buying_rate[item_code] = flt(frappe.db.sql("""
					select sum(base_net_amount) / sum(qty * conversion_factor)
					from `tabPurchase Invoice Item`
					where item_code = %s and docstatus=1""", item_code)[0][0])
			else:
				args.update({
					'voucher_type': row.parenttype,
					'voucher_no': row.parent,
					'allow_zero_valuation': True,
					'company': self.filters.company
				})

				average_buying_rate = get_incoming_rate(args)
				self.average_buying_rate[item_code] =  flt(average_buying_rate)

		return self.average_buying_rate[item_code]

	def get_last_purchase_rate(self, item_code):
		if self.filters.to_date:
			last_purchase_rate = frappe.db.sql("""
			select (a.base_rate / a.conversion_factor)
			from `tabPurchase Invoice Item` a
			where a.item_code = %s and a.docstatus=1
			and modified <= %s
			order by a.modified desc limit 1""", (item_code,self.filters.to_date))
		else:
			last_purchase_rate = frappe.db.sql("""
			select (a.base_rate / a.conversion_factor)
			from `tabPurchase Invoice Item` a
			where a.item_code = %s and a.docstatus=1
			order by a.modified desc limit 1""", item_code)
		return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0

	def load_invoice_items(self):
		conditions = ""
		if self.filters.company:
			conditions += " and company = %(company)s"
		if self.filters.from_date:
			conditions += " and posting_date >= %(from_date)s"
		if self.filters.to_date:
			conditions += " and posting_date <= %(to_date)s"

		if self.filters.group_by=="Sales Person":
			sales_person_cols = ", sales.sales_person, sales.allocated_amount, sales.incentives"
			sales_team_table = "left join `tabSales Team` sales on sales.parent = `tabSales Invoice`.name"
		else:
			sales_person_cols = ""
			sales_team_table = ""

		self.si_list = frappe.db.sql("""
			select
				`tabSales Invoice Item`.parenttype, `tabSales Invoice Item`.parent,
				`tabSales Invoice`.posting_date, `tabSales Invoice`.posting_time,
				`tabSales Invoice`.project, `tabSales Invoice`.update_stock,
				`tabSales Invoice`.customer, `tabSales Invoice`.customer_group,
				`tabSales Invoice`.territory, `tabSales Invoice Item`.item_code,
				`tabSales Invoice Item`.item_name, `tabSales Invoice Item`.description,
				`tabSales Invoice Item`.warehouse, `tabSales Invoice Item`.item_group,
				`tabSales Invoice Item`.brand, `tabSales Invoice Item`.dn_detail,
				`tabSales Invoice Item`.delivery_note, `tabSales Invoice Item`.stock_qty as qty,
				`tabSales Invoice Item`.base_net_rate, `tabSales Invoice Item`.base_net_amount,
				`tabSales Invoice Item`.name as "item_row", `tabSales Invoice`.is_return
				{sales_person_cols}
			from
				`tabSales Invoice` inner join `tabSales Invoice Item`
					on `tabSales Invoice Item`.parent = `tabSales Invoice`.name
				{sales_team_table}
			where
				`tabSales Invoice`.docstatus=1 {conditions} {match_cond}
			order by
				`tabSales Invoice`.posting_date desc, `tabSales Invoice`.posting_time desc"""
			.format(conditions=conditions, sales_person_cols=sales_person_cols,
				sales_team_table=sales_team_table, match_cond = get_match_cond('Sales Invoice')), self.filters, as_dict=1)

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
