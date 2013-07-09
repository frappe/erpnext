# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)
	item_map = get_item_details()
	pl = get_price_list()
	last_purchase_rate = get_last_purchase_rate()
	bom_rate = get_item_bom_rate()
	val_rate_map = get_valuation_rate()

	precision = webnotes.conn.get_value("Global Defaults", None, "float_precision") or 2
	
	data = []
	for item in sorted(item_map):
		data.append([item, item_map[item]["item_name"], 
			item_map[item]["description"], item_map[item]["stock_uom"], 
			flt(last_purchase_rate.get(item, 0), precision), 
			flt(val_rate_map.get(item, 0), precision), 
			pl.get(item, {}).get("selling"), 
			pl.get(item, {}).get("buying"), 
			flt(bom_rate.get(item, 0), precision), 
			flt(item_map[item]["standard_rate"], precision)
		])
	
	return columns, data

def get_columns(filters):
	"""return columns based on filters"""
	
	columns = ["Item:Link/Item:100", "Item Name::150", "Description::150", "UOM:Link/UOM:80", 
		"Last Purchase Rate:Currency:90", "Valuation Rate:Currency:80",	"Sales Price List::80", 
		"Purchase Price List::80", "BOM Rate:Currency:90", "Standard Rate:Currency:100"]

	return columns

def get_item_details():
	"""returns all items details"""
	
	item_map = {}
	
	for i in webnotes.conn.sql("select name, item_name, description, \
		stock_uom, standard_rate from tabItem \
		order by item_code", as_dict=1):
			item_map.setdefault(i.name, i)

	return item_map

def get_price_list():
	"""Get selling & buying price list of every item"""

	rate = {}
	
	price_list = webnotes.conn.sql("""select parent, selling, buying, 
		concat(price_list_name, " - ", ref_currency, " ", ref_rate) as price
		from `tabItem Price` where docstatus<2""", as_dict=1)

	for j in price_list:
		if j.price:
			if j.selling:
				rate.setdefault(j.parent, {}).setdefault("selling", []).append(j.price)
			if j.buying:
				rate.setdefault(j.parent, {}).setdefault("buying", []).append(j.price)

	item_rate_map = {}
	
	for item in rate:
		item_rate_map.setdefault(item, {}).setdefault("selling", 
			", ".join(rate[item].get("selling", [])))
		item_rate_map[item]["buying"] = ", ".join(rate[item].get("buying", []))
	
	return item_rate_map

def get_last_purchase_rate():

	item_last_purchase_rate_map = {}

	query = """select * from (select 
					result.item_code,
					result.purchase_rate
					from (
						(select 
							po_item.item_code,
							po_item.item_name,
							po.transaction_date as posting_date,
							po_item.purchase_ref_rate, 
							po_item.discount_rate, 
							po_item.purchase_rate
						from `tabPurchase Order` po, `tabPurchase Order Item` po_item
						where po.name = po_item.parent and po.docstatus = 1)
						union
						(select 
							pr_item.item_code,
							pr_item.item_name,
							pr.posting_date,
							pr_item.purchase_ref_rate,
							pr_item.discount_rate,
							pr_item.purchase_rate
						from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
						where pr.name = pr_item.parent and pr.docstatus = 1)
				) result
				order by result.item_code asc, result.posting_date desc) result_wrapper
				group by item_code"""

	for d in webnotes.conn.sql(query, as_dict=1):
		item_last_purchase_rate_map.setdefault(d.item_code, d.purchase_rate)

	return item_last_purchase_rate_map

def get_item_bom_rate():
	"""Get BOM rate of an item from BOM"""

	item_bom_map = {}
	
	for b in webnotes.conn.sql("""select item, (total_cost/quantity) as bom_rate 
		from `tabBOM` where is_active=1 and is_default=1""", as_dict=1):
			item_bom_map.setdefault(b.item, flt(b.bom_rate))

	return item_bom_map

def get_valuation_rate():
	"""Get an average valuation rate of an item from all warehouses"""

	item_val_rate_map = {}
	
	for d in webnotes.conn.sql("""select item_code, 
		sum(actual_qty*valuation_rate)/sum(actual_qty) as val_rate
		from tabBin where actual_qty > 0 group by item_code""", as_dict=1):
			item_val_rate_map.setdefault(d.item_code, d.val_rate)

	return item_val_rate_map
