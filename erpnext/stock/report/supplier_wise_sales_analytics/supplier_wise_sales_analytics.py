# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns(filters)
	consumed_details = get_consumed_details(filters)
	supplier_details = get_suppliers_details(filters)
	material_transfer_vouchers = get_material_transfer_vouchers()
	data = []

	for item_code, suppliers in supplier_details.items():
		consumed_qty = consumed_amount = delivered_qty = delivered_amount = 0.0
		total_qty = total_amount = 0.0
		if consumed_details.get(item_code):
			for cd in consumed_details.get(item_code):

				if cd.voucher_no not in material_transfer_vouchers:
					if cd.voucher_type in ["Delivery Note", "Sales Invoice"]:
						delivered_qty += abs(flt(cd.actual_qty))
						delivered_amount += abs(flt(cd.stock_value_difference))
					elif cd.voucher_type != "Delivery Note":
						consumed_qty += abs(flt(cd.actual_qty))
						consumed_amount += abs(flt(cd.stock_value_difference))

			if consumed_qty or consumed_amount or delivered_qty or delivered_amount:
				total_qty += delivered_qty + consumed_qty
				total_amount += delivered_amount + consumed_amount

				row = [
					cd.item_code,
					cd.item_name,
					cd.description,
					cd.stock_uom,
					consumed_qty,
					consumed_amount,
					delivered_qty,
					delivered_amount,
					total_qty,
					total_amount,
					",".join(list(set(suppliers))),
				]
				data.append(row)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = (
		[_("Item") + ":Link/Item:100"]
		+ [_("Item Name") + "::100"]
		+ [_("Description") + "::150"]
		+ [_("UOM") + ":Link/UOM:90"]
		+ [_("Consumed Qty") + ":Float:110"]
		+ [_("Consumed Amount") + ":Currency:130"]
		+ [_("Delivered Qty") + ":Float:110"]
		+ [_("Delivered Amount") + ":Currency:130"]
		+ [_("Total Qty") + ":Float:110"]
		+ [_("Total Amount") + ":Currency:130"]
		+ [_("Supplier(s)") + "::250"]
	)

	return columns


def get_conditions(filters):
	conditions = ""
	values = []

	if filters.get("from_date") and filters.get("to_date"):
		conditions = "and sle.posting_date>=%s and sle.posting_date<=%s"
		values = [filters.get("from_date"), filters.get("to_date")]

	return conditions, values


def get_consumed_details(filters):
	conditions, values = get_conditions(filters)
	consumed_details = {}

	for d in frappe.db.sql(
		"""select sle.item_code, i.item_name, i.description,
		i.stock_uom, sle.actual_qty, sle.stock_value_difference,
		sle.voucher_no, sle.voucher_type
		from `tabStock Ledger Entry` sle, `tabItem` i
		where sle.is_cancelled = 0 and sle.item_code=i.name and sle.actual_qty < 0 %s"""
		% conditions,
		values,
		as_dict=1,
	):
		consumed_details.setdefault(d.item_code, []).append(d)

	return consumed_details


def get_suppliers_details(filters):
	item_supplier_map = {}
	supplier = filters.get("supplier")

	for d in frappe.db.sql(
		"""select pr.supplier, pri.item_code from
		`tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
		where pr.name=pri.parent and pr.docstatus=1 and
		pri.item_code=(select name from `tabItem` where
			is_stock_item=1 and name=pri.item_code)""",
		as_dict=1,
	):
		item_supplier_map.setdefault(d.item_code, []).append(d.supplier)

	for d in frappe.db.sql(
		"""select pr.supplier, pri.item_code from
		`tabPurchase Invoice` pr, `tabPurchase Invoice Item` pri
		where pr.name=pri.parent and pr.docstatus=1 and
		ifnull(pr.update_stock, 0) = 1 and pri.item_code=(select name from `tabItem`
			where is_stock_item=1 and name=pri.item_code)""",
		as_dict=1,
	):
		if d.item_code not in item_supplier_map:
			item_supplier_map.setdefault(d.item_code, []).append(d.supplier)

	if supplier:
		invalid_items = []
		for item_code, suppliers in item_supplier_map.items():
			if supplier not in suppliers:
				invalid_items.append(item_code)

		for item_code in invalid_items:
			del item_supplier_map[item_code]

	return item_supplier_map


def get_material_transfer_vouchers():
	return frappe.db.sql_list(
		"""select name from `tabStock Entry` where
		purpose='Material Transfer' and docstatus=1"""
	)
