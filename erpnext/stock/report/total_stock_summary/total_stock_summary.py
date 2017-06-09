# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
import datetime


def execute(filters=None):
    if not filters: filters = {}

    validate_filters(filters)

    columns = get_columns()
    item_map = get_item_details()
    iwb_map = get_item_warehouse_map()
    ic_map = c_get_item_warehouse_map()

    data = []
    total_bal = 0

    if (filters.get("group_by") == 'Company'):
        for (company, item) in sorted(ic_map):
            c_qty_dict = ic_map[(company, item)]
            data.append([company, item, item_map[item]["item_name"],
                         item_map[item]["item_group"],
                         "",
                         item_map[item]["stock_uom"], c_qty_dict.bal_qty,
                         ])
    else:
        for (company, item, warehouse) in sorted(iwb_map):
            qty_dict = iwb_map[(company, item, warehouse)]
            data.append([company, item, item_map[item]["item_name"],
                         item_map[item]["item_group"], warehouse,
                         item_map[item]["stock_uom"], qty_dict.bal_qty,
                         ])

    return columns, data


def get_columns():
    """return columns"""
    columns = [
        _("Company") + ":Link/Company:250",
        _("Item") + ":Link/Item:200",
        _("Item Name") + "::150",
        _("Item Group") + "::100",
        # _("Brand") + "::90",
        # _("Description") + "::140",
        _("Warehouse") + ":Link/Warehouse:150",
        _("Stock UOM") + ":Link/UOM:90",
        _("Balance Qty") + ":Float:100",
    ]

    return columns


def get_stock_ledger_entries():
    now = datetime.date.today()

    return frappe.db.sql("""
		select
			sle.item_code, warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		where sle.docstatus < 2 and sle.posting_date <= %s
		order by sle.posting_date, sle.posting_time, sle.name""" %
                         (now), as_dict=1)


def get_item_warehouse_map():
    iwb_map = {}
    now = datetime.date.today()

    sle = get_stock_ledger_entries()

    for d in sle:
        key = (d.company, d.item_code, d.warehouse)
        if key not in iwb_map:
            iwb_map[key] = frappe._dict({
                "opening_qty": 0.0, "opening_val": 0.0,
                "in_qty": 0.0, "in_val": 0.0,
                "out_qty": 0.0, "out_val": 0.0,
                "bal_qty": 0.0, "bal_val": 0.0,
                "val_rate": 0.0
            })

        qty_dict = iwb_map[(d.company, d.item_code, d.warehouse)]

        if d.voucher_type == "Stock Reconciliation":
            qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
        else:
            qty_diff = flt(d.actual_qty)

        value_diff = flt(d.stock_value_difference)

        # if d.posting_date < from_date:
        qty_dict.opening_qty += qty_diff
        qty_dict.opening_val += value_diff

        if d.posting_date <= now:
            if qty_diff > 0:
                qty_dict.in_qty += qty_diff
                qty_dict.in_val += value_diff
            else:
                qty_dict.out_qty += abs(qty_diff)
                qty_dict.out_val += abs(value_diff)

        qty_dict.val_rate = d.valuation_rate
        qty_dict.bal_qty += qty_diff
        qty_dict.bal_val += value_diff

    iwb_map = filter_items_with_no_transactions(iwb_map)

    return iwb_map

def c_get_item_warehouse_map():
    ic_map = {}
    now = datetime.date.today()

    sle = get_stock_ledger_entries()

    for d in sle:
        key = (d.company, d.item_code)
        if key not in ic_map:
            ic_map[key] = frappe._dict({
                "opening_qty": 0.0, "opening_val": 0.0,
                "in_qty": 0.0, "in_val": 0.0,
                "out_qty": 0.0, "out_val": 0.0,
                "bal_qty": 0.0, "bal_val": 0.0,
                "val_rate": 0.0
            })

        qty_dict = ic_map[(d.company, d.item_code)]

        if d.voucher_type == "Stock Reconciliation":
            qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
        else:
            qty_diff = flt(d.actual_qty)

        value_diff = flt(d.stock_value_difference)

        # if d.posting_date < from_date:
        qty_dict.opening_qty += qty_diff
        qty_dict.opening_val += value_diff

        if d.posting_date <= now:
            if qty_diff > 0:
                qty_dict.in_qty += qty_diff
                qty_dict.in_val += value_diff
            else:
                qty_dict.out_qty += abs(qty_diff)
                qty_dict.out_val += abs(value_diff)

        qty_dict.val_rate = d.valuation_rate
        qty_dict.bal_qty += qty_diff
        qty_dict.bal_val += value_diff

        ic_map = c_filter_items_with_no_transactions(ic_map)

    return ic_map


def filter_items_with_no_transactions(iwb_map):
    for (company, item, warehouse) in sorted(iwb_map):
        qty_dict = iwb_map[(company, item, warehouse)]

        no_transactions = True
        for key, val in qty_dict.items():
            val = flt(val, 3)
            qty_dict[key] = val
            if key != "val_rate" and val:
                no_transactions = False

        if no_transactions:
            iwb_map.pop((company, item, warehouse))

    return iwb_map

def c_filter_items_with_no_transactions(ic_map):
    for (company, item, warehouse) in sorted(ic_map):
        qty_dict = ic_map[(company, item)]

        no_transactions = True
        for key, val in qty_dict.items():
            val = flt(val, 3)
            qty_dict[key] = val
            if key != "val_rate" and val:
                no_transactions = False

        if no_transactions:
            ic_map.pop((company, item))

    return ic_map


def get_item_details():
    condition = ''
    value = ()

    items = frappe.db.sql("""select name, item_name, stock_uom, item_group, brand, description
		from tabItem {condition}""".format(condition=condition), value, as_dict=1)

    return dict((d.name, d) for d in items)


def validate_filters(filters):
    if (filters.get("group_by") == 'Company') and filters.get("company"):
        frappe.throw(_("Please set Company filter Blank if Group By is 'Company'"))