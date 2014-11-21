# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.gross_profit_common import GrossProfitGenerator

def execute(filters=None):
	if not filters: filters = {}
	filters.update({"group_by": "name"})
	source_data = GrossProfitGenerator(filters)

	print source_data.retr()

	return None, None

# 	columns = get_columns(filters.group_by)
	
# 	data = []
# 	for row in source_data:
# 		print row

# 	return columns, data

# def get_columns(group_by):
# 	pass

# def get_data(group_by, source_data):
# 	pass

# def execute(filters=None):
# 	if not filters: filters = {}

# 	stock_ledger_entries = get_stock_ledger_entries(filters)
# 	source = get_source_data(filters)
# 	item_sales_bom = get_item_sales_bom()

# 	columns = [_("Sales Invoice") + "::120", _("Link") + "::30", _("Posting Date") + ":Date", _("Posting Time"),
# 		_("Item Code") + ":Link/Item", _("Item Name"), _("Description"), _("Warehouse") + ":Link/Warehouse",
# 		_("Qty") + ":Float", _("Selling Rate") + ":Currency", _("Avg. Buying Rate") + ":Currency",
# 		_("Selling Amount") + ":Currency", _("Buying Amount") + ":Currency",
# 		_("Gross Profit") + ":Currency", _("Gross Profit %") + ":Percent", _("Project") + ":Link/Project"]
# 	data = []
# 	for row in source:
# 		selling_amount = flt(row.base_amount)
# 		total_selling_amount += flt(row.base_amount)

# 		item_sales_bom_map = item_sales_bom.get(row.parenttype, {}).get(row.name, frappe._dict())

# 		if item_sales_bom_map.get(row.item_code):
# 			buying_amount = get_sales_bom_buying_amount(row.item_code, row.warehouse,
# 				row.parenttype, row.name, row.item_row, stock_ledger_entries, item_sales_bom_map)
# 		else:
# 			buying_amount = get_buying_amount(row.item_code, row.qty, row.parenttype, row.name, row.item_row,
# 				stock_ledger_entries.get((row.item_code, row.warehouse), []))

# 		buying_amount = buying_amount > 0 and buying_amount or 0
# 		total_buying_amount += buying_amount

# 		gross_profit = selling_amount - buying_amount
# 		total_gross_profit += gross_profit

# 		if selling_amount:
# 			gross_profit_percent = (gross_profit / selling_amount) * 100.0
# 		else:
# 			gross_profit_percent = 0.0

# 		icon = """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
# 			% ("/".join(["#Form", row.parenttype, row.name]),)
# 		data.append([row.name, icon, row.posting_date, row.posting_time, row.item_code, row.item_name,
# 			row.description, row.warehouse, row.qty, row.base_rate,
# 			row.qty and (buying_amount / row.qty) or 0, row.base_amount, buying_amount,
# 			gross_profit, gross_profit_percent, row.project])

# 	if total_selling_amount:
# 		total_gross_profit_percent = (total_gross_profit / total_selling_amount) * 100.0
# 	else:
# 		total_gross_profit_percent = 0.0

# 	data.append(["Total", None, None, None, None, None, None, None, None, None, None, total_selling_amount,
# 		total_buying_amount, total_gross_profit, total_gross_profit_percent, None])

# 	return columns, data
