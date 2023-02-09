# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	pl = get_price_list()
	last_purchase_rate = get_last_purchase_rate()
	bom_rate = get_item_bom_rate()
	val_rate_map = get_valuation_rate()

	from erpnext.accounts.utils import get_currency_precision

	precision = get_currency_precision() or 2
	data = []
	for item in sorted(item_map):
		data.append(
			[
				item,
				item_map[item]["item_name"],
				item_map[item]["item_group"],
				item_map[item]["brand"],
				item_map[item]["description"],
				item_map[item]["stock_uom"],
				flt(last_purchase_rate.get(item, 0), precision),
				flt(val_rate_map.get(item, 0), precision),
				pl.get(item, {}).get("Selling"),
				pl.get(item, {}).get("Buying"),
				flt(bom_rate.get(item, 0), precision),
			]
		)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		_("Item") + ":Link/Item:100",
		_("Item Name") + "::150",
		_("Item Group") + ":Link/Item Group:125",
		_("Brand") + "::100",
		_("Description") + "::150",
		_("UOM") + ":Link/UOM:80",
		_("Last Purchase Rate") + ":Currency:90",
		_("Valuation Rate") + ":Currency:80",
		_("Sales Price List") + "::180",
		_("Purchase Price List") + "::180",
		_("BOM Rate") + ":Currency:90",
	]

	return columns


def get_item_details(filters):
	"""returns all items details"""

	item_map = {}

	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_group, item.item_name, item.description, item.brand, item.stock_uom)
		.orderby(item.item_code, item.item_group)
	)

	if filters.get("items") == "Enabled Items only":
		query = query.where(item.disabled == 0)
	elif filters.get("items") == "Disabled Items only":
		query = query.where(item.disabled == 1)

	for i in query.run(as_dict=True):
		item_map.setdefault(i.name, i)

	return item_map


def get_price_list():
	"""Get selling & buying price list of every item"""

	rate = {}

	ip = frappe.qb.DocType("Item Price")
	pl = frappe.qb.DocType("Price List")
	cu = frappe.qb.DocType("Currency")

	price_list = (
		frappe.qb.from_(ip)
		.from_(pl)
		.from_(cu)
		.select(
			ip.item_code,
			ip.buying,
			ip.selling,
			(IfNull(cu.symbol, ip.currency)).as_("currency"),
			ip.price_list_rate,
			ip.price_list,
		)
		.where((ip.price_list == pl.name) & (pl.currency == cu.name) & (pl.enabled == 1))
	).run(as_dict=True)

	for d in price_list:
		d.update(
			{"price": "{0} {1} - {2}".format(d.currency, round(d.price_list_rate, 2), d.price_list)}
		)
		d.pop("currency")
		d.pop("price_list_rate")
		d.pop("price_list")

		if d.price:
			rate.setdefault(d.item_code, {}).setdefault("Buying" if d.buying else "Selling", []).append(
				d.price
			)

	item_rate_map = {}

	for item in rate:
		for buying_or_selling in rate[item]:
			item_rate_map.setdefault(item, {}).setdefault(
				buying_or_selling, ", ".join(rate[item].get(buying_or_selling, []))
			)

	return item_rate_map


def get_last_purchase_rate():
	item_last_purchase_rate_map = {}

	po = frappe.qb.DocType("Purchase Order")
	pr = frappe.qb.DocType("Purchase Receipt")
	pi = frappe.qb.DocType("Purchase Invoice")
	po_item = frappe.qb.DocType("Purchase Order Item")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(
			(
				frappe.qb.from_(po)
				.from_(po_item)
				.select(po_item.item_code, po.transaction_date.as_("posting_date"), po_item.base_rate)
				.where((po.name == po_item.parent) & (po.docstatus == 1))
			)
			+ (
				frappe.qb.from_(pr)
				.from_(pr_item)
				.select(pr_item.item_code, pr.posting_date, pr_item.base_rate)
				.where((pr.name == pr_item.parent) & (pr.docstatus == 1))
			)
			+ (
				frappe.qb.from_(pi)
				.from_(pi_item)
				.select(pi_item.item_code, pi.posting_date, pi_item.base_rate)
				.where((pi.name == pi_item.parent) & (pi.docstatus == 1) & (pi.update_stock == 1))
			)
		)
		.select("*")
		.orderby("item_code", "posting_date")
	)

	for d in query.run(as_dict=True):
		item_last_purchase_rate_map[d.item_code] = d.base_rate

	return item_last_purchase_rate_map


def get_item_bom_rate():
	"""Get BOM rate of an item from BOM"""

	item_bom_map = {}

	bom = frappe.qb.DocType("BOM")
	bom_data = (
		frappe.qb.from_(bom)
		.select(bom.item, (bom.total_cost / bom.quantity).as_("bom_rate"))
		.where((bom.is_active == 1) & (bom.is_default == 1))
	).run(as_dict=True)

	for d in bom_data:
		item_bom_map.setdefault(d.item, flt(d.bom_rate))

	return item_bom_map


def get_valuation_rate():
	"""Get an average valuation rate of an item from all warehouses"""

	item_val_rate_map = {}

	bin = frappe.qb.DocType("Bin")
	bin_data = (
		frappe.qb.from_(bin)
		.select(
			bin.item_code, Sum(bin.actual_qty * bin.valuation_rate) / Sum(bin.actual_qty).as_("val_rate")
		)
		.where(bin.actual_qty > 0)
		.groupby(bin.item_code)
	).run(as_dict=True)

	for d in bin_data:
		item_val_rate_map.setdefault(d.item_code, d.val_rate)

	return item_val_rate_map
