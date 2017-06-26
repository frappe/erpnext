# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    if not filters: filters = {}
    validate_filters(filters)
    columns = get_columns()
    data = []
    stock = get_total_stock(filters)

    for row in stock:
        if filters.get("group_by") == "Warehouse":
            data.append(["", row.warehouse, row.item_code, row.description, row.actual_qty])
        else:
            data.append([row.company, "", row.item_code, row.description, row.actual_qty])

    return columns, data


def get_columns():
    columns = [
        _("Company") + ":Link/Item:250",
        _("Warehouse") + ":Link/Item:150",
        _("Item") + ":Link/Item:150",
        _("Description") + "::300",
        _("Current Qty") + ":Float:100",
    ]

    return columns


def get_total_stock(filters):
    conditions = ""
    columns = ""

    if filters.get("group_by") == "Warehouse":
        if filters.get("company"):
            conditions += " AND warehouse.company = '%s' GROUP BY ledger.warehouse, item.item_code" % frappe.db.escape(
                filters.get("company"), percent=False)
        else:
            conditions += " GROUP BY ledger.warehouse, item.item_code"
        columns += " ledger.warehouse, item.item_code , item.description , sum(ledger.actual_qty) as actual_qty"
    else:
        conditions += " GROUP BY warehouse.company, item.item_code"
        columns += " warehouse.company, item.item_code , item.description , sum(ledger.actual_qty) as actual_qty"

    return frappe.db.sql("""
    		SELECT
                %s
            FROM
    	        `tabBin` AS ledger
    	        INNER JOIN `tabItem` AS item
    		    ON ledger.item_code = item.item_code
    		    INNER JOIN `tabWarehouse` warehouse
    		    ON warehouse.name = ledger.warehouse
    		WHERE
    			actual_qty != 0
    	        %s""" % (columns, conditions), as_dict=1)


def validate_filters(filters):
    if (filters.get("group_by") == 'Company') and filters.get("company"):
        frappe.throw(_("Please set Company filter Blank if Group By is 'Company'"))