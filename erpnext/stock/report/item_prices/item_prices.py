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
	sn = get_supplier_name()
	pl = get_price_list()
	last_purchase_rate = get_last_purchase_rate()
	bom_rate = get_item_bom_rate()
	val_rate_map = get_valuation_rate()

	from erpnext.accounts.utils import get_currency_precision
	precision = get_currency_precision() or 2
	data = []
	for item in sorted(item_map):
		data.append([item, item_map[item]["item_name"],item_map[item]["item_group"],
			item_map[item]["description"],
			flt(last_purchase_rate.get(item, 0), precision),
			sn.get(item, {}).get("supplier"),
			sn.get(item, {}).get("supplier_name"),
			sn.get(item, {}).get("supplier_part_no"),
			pl.get(item, {}).get("Selling"),
			pl.get(item, {}).get("Buying"),
			item_map[item]["manufacturer"],
			item_map[item]["manufacturer_part_no"],
			item_map[item]["stock_uom"],
			flt(val_rate_map.get(item, {}).get("balance_qty"), precision),
            flt(val_rate_map.get(item, {}).get("val_rate"), precision),
			flt(bom_rate.get(item, 0), precision),
            item_map[item]["parent_website_route"]
		])


	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:125",
		_("Item Name") + "::150",
		_("Item Group") + ":Link/Item Group:125",
		_("Description") + "::200",
		_("Last Purchase Rate") + ":Currency:90",
		_("Supplier") + ":Link/Supplier:100",
		_("Supplier Name") + "::150",
		_("Supplier Part No") + "::125",
		_("Sales Price List") + "::80",
		_("Purchase Price List") + "::80",
		_("Manufacturer") + "::100",
		_("Manufacturer Part No") + "::100",
		_("UOM") + ":Link/UOM:80",
		_("Balance Qty") + ":Float:80",
		_("Valuation Rate") + ":Currency:90",
		_("BOM Rate") + ":Currency:90",
		_("Parent Website Route") + "::200"]
	
	return columns

def get_item_details():
	"""returns all items details"""

	item_map = {}

	for i in frappe.db.sql("select it.item_group as item_group, it.name as name, item_name, it.description as description, \
		stock_uom, manufacturer, manufacturer_part_no, itg.parent_website_route as parent_website_route from tabItem it, `tabItem Group` itg \
        where it.item_group = itg.name \
		order by it.item_group, item_code", as_dict=1):
			item_map.setdefault(i.name, i)

	return item_map

def get_price_list():
	"""Get selling & buying price list of every item"""

	rate = {}

	price_list = frappe.db.sql("""select ip.item_code, ip.buying, ip.selling,
		concat(ip.price_list, " - ", ip.currency, " ", ip.price_list_rate) as price
		from `tabItem Price` ip, `tabPrice List` pl
		where ip.price_list=pl.name and pl.enabled=1""", as_dict=1)

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
		sum(actual_qty*valuation_rate)/sum(actual_qty) as val_rate, sum(actual_qty) as balance_qty
		from tabBin where actual_qty > 0 group by item_code""", as_dict=1):
			item_val_rate_map.setdefault(d.item_code, {}).setdefault("val_rate",d.val_rate)
			item_val_rate_map.setdefault(d.item_code, {}).setdefault("balance_qty",d.balance_qty)

	return item_val_rate_map

def get_supplier_name():
	"""returns supplier name"""

	supplier_name_map = {}

	for i in frappe.db.sql("""select it.parent, it.supplier, su.supplier_name, it.supplier_part_no \
		from `tabItem Supplier` it, `tabSupplier` su where it.supplier=su.name\
		order by parent, supplier""", as_dict=1):
			supplier_name_map.setdefault(i.parent, {}).setdefault("supplier", i.supplier)
			supplier_name_map.setdefault(i.parent, {}).setdefault("supplier_name", i.supplier_name)
			supplier_name_map.setdefault(i.parent, {}).setdefault("supplier_part_no", i.supplier_part_no)

	return supplier_name_map
