# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    if not filters: filters = {}
    columns = get_columns()

    if filters.get('multilevel'):
        data = get_exploded_bom_stock(filters)
    else:
        data = get_bom_stock(filters)
    
    return columns, data

def get_columns():
    """return columns"""
    columns = [
        _("Item") + ":Link/Item:150",
        _("Description") + "::500",
        _("Required Qty") + ":Float:100",
        _("In Stock Qty") + ":Float:100",
        _("Enough Parts to Build") + ":Float:200",
    ]

    return columns

def get_bom_stock(filters):
    conditions = ""
    bom = filters.get("bom")

    if filters.get("warehouse"):
        warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
        if warehouse_details:
            conditions += " and exists (select name from `tabWarehouse` wh \
        	    where wh.lft >= %s and wh.rgt <= %s and ledger.warehouse = wh.name)" % (warehouse_details.lft,
                warehouse_details.rgt)
        else:
            conditions += " and ledger.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"))

    else:
        conditions += ""

    return frappe.db.sql("""
    		SELECT
    	        bom_item.item_code ,
    	        bom_item.description ,
    	        bom_item.qty,
    	        sum(ledger.actual_qty) as actual_qty,
    	        sum(FLOOR(ledger.actual_qty /bom_item.qty))as to_build
            FROM
    	        `tabBOM Item` AS bom_item
    	        LEFT JOIN `tabBin` AS ledger
    		    ON bom_item.item_code = ledger.item_code
    		    %s
            WHERE
    	        bom_item.parent = '%s' and bom_item.parenttype='BOM'

            GROUP BY bom_item.item_code""" % (conditions, bom))


def get_exploded_bom_stock(filters):
    root_bom_name = filters.get("bom")
    root_bom = frappe.get_doc("BOM", root_bom_name)

    bom_tree_list = root_bom.traverse_tree()

    out = ()

    filters_for_multilevel = frappe._dict(bom=None, warehouse=filters.get("warehouse"))

    for sub_bom in bom_tree_list:
        filters_for_multilevel.bom = sub_bom
        out += get_bom_stock(filters_for_multilevel)

    return out