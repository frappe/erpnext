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
	bom_rate = get_item_bom_rate()
	val_rate_map = get_valuation_rate()
	
	data = []
	for item in sorted(item_map):
		data.append([item, item_map[item]["item_name"], 
			item_map[item]["description"], item_map[item]["stock_uom"], 
			flt(item_map[item]["last_purchase_rate"]), val_rate_map.get(item, 0), 
			pl.get(item, {}).get("selling"), pl.get(item, {}).get("buying"), 
			bom_rate.get(item, 0), flt(item_map[item]["standard_rate"])
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
		stock_uom, standard_rate, last_purchase_rate from tabItem \
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

def get_item_bom_rate():
	"""Get BOM rate of an item from BOM"""

	bom_map = {}
	
	for b in webnotes.conn.sql("""select item, (total_cost/quantity) as bom_rate 
		from `tabBOM` where is_active=1 and is_default=1""", as_dict=1):
			bom_map.setdefault(b.item, flt(b.bom_rate))

	return bom_map

def get_valuation_rate():
	"""Get an average valuation rate of an item from all warehouses"""

	val_rate_map = {}
	
	for d in webnotes.conn.sql("""select item_code, avg(valuation_rate) as val_rate
		from tabBin group by item_code""", as_dict=1):
			val_rate_map.setdefault(d.item_code, d.val_rate)

	return val_rate_map