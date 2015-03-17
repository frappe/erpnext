# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.utilities.repost_stock import update_bin_qty, get_reserved_qty

def execute():
	for item_code, warehouse in frappe.db.sql("select item_code, warehouse from tabBin where ifnull(reserved_qty, 0) < 0"):
		update_bin_qty(item_code, warehouse, {
			"reserved_qty": get_reserved_qty(item_code, warehouse)
		})