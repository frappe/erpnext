# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	item_map = get_item_details()
	pl = get_price_list()
	last_purchase_rate = get_last_purchase_rate()
	bom_rate = get_item_bom_rate()
	val_rate_map = get_valuation_rate()

	from erpnext.accounts.utils import get_currency_precision
	precision = get_currency_precision() or 2
	data = []
	for item in sorted(item_map):
		data.append([item, item_map[item]["item_name"],item_map[item]["item_group"],
			item_map[item]["description"], item_map[item]["stock_uom"],
			flt(last_purchase_rate.get(item, 0), precision),
			flt(val_rate_map.get(item, 0), precision),
			pl.get(item, {}).get("Selling"),
			pl.get(item, {}).get("Buying"),
			flt(bom_rate.get(item, 0), precision)
		])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:100", _("Item Name") + "::150",_("Item Group") + ":Link/Item Group:125", _("Description") + "::150", _("UOM") + ":Link/UOM:80",
		_("Last Purchase Rate") + ":Currency:90", _("Valuation Rate") + ":Currency:80",	_("Sales Price List") + "::180",
		_("Purchase Price List") + "::180", _("BOM Rate") + ":Currency:90"]

	return columns

def get_item_details():
	"""returns all items details"""

	item_map = {}

	for i in frappe.db.sql("select name, item_group, item_name, description, \
		stock_uom from tabItem \
		order by item_code, item_group", as_dict=1):
			item_map.setdefault(i.name, i)

	return item_map

def get_price_list():
	"""Get selling & buying price list of every item"""

	rate = {}

	price_list = frappe.db.sql("""select ip.item_code, ip.buying, ip.selling,
		concat(ifnull(cu.symbol,ip.currency), " ", round(ip.price_list_rate,2), " - ", ip.price_list) as price
		from `tabItem Price` ip, `tabPrice List` pl, `tabCurrency` cu
		where ip.price_list=pl.name and pl.currency=cu.name and pl.enabled=1""", as_dict=1)

	for j in price_list:
		if j.price:
			rate.setdefault(j.item_code, {}).setdefault("Buying" if j.buying else "Selling", []).append(j.price)
	item_rate_map = {}

	for item in rate:
		for buying_or_selling in rate[item]:
			item_rate_map.setdefault(item, {}).setdefault(buying_or_selling,
				", ".join(rate[item].get(buying_or_selling, [])))

	return item_rate_map

def get_last_purchase_rate():

	item_last_purchase_rate_map = {}

	query = """select * from (select
					result.item_code,
					result.base_rate
					from (
						(select
							po_item.item_code,
							po_item.item_name,
							po.transaction_date as posting_date,
							po_item.base_price_list_rate,
							po_item.discount_percentage,
							po_item.base_rate
						from `tabPurchase Order` po, `tabPurchase Order Item` po_item
						where po.name = po_item.parent and po.docstatus = 1)
						union
						(select
							pr_item.item_code,
							pr_item.item_name,
							pr.posting_date,
							pr_item.base_price_list_rate,
							pr_item.discount_percentage,
							pr_item.base_rate
						from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
						where pr.name = pr_item.parent and pr.docstatus = 1)
				) result
				order by result.item_code asc, result.posting_date desc) result_wrapper
				group by item_code"""

	for d in frappe.db.sql(query, as_dict=1):
		item_last_purchase_rate_map.setdefault(d.item_code, d.base_rate)

	return item_last_purchase_rate_map

def get_item_bom_rate():
	"""Get BOM rate of an item from BOM"""

	item_bom_map = {}

	for b in frappe.db.sql("""select item, (total_cost/quantity) as bom_rate
		from `tabBOM` where is_active=1 and is_default=1""", as_dict=1):
			item_bom_map.setdefault(b.item, flt(b.bom_rate))

	return item_bom_map

def get_valuation_rate():
	"""Get an average valuation rate of an item from all warehouses"""

	item_val_rate_map = {}

	for d in frappe.db.sql("""select item_code,
		sum(actual_qty*valuation_rate)/sum(actual_qty) as val_rate
		from tabBin where actual_qty > 0 group by item_code""", as_dict=1):
			item_val_rate_map.setdefault(d.item_code, d.val_rate)

	return item_val_rate_map
