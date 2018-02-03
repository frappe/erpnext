# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vlog import vwrite
import json
@frappe.whitelist()
def get_ebay_m2m_details_for_so(sales_order):
	buyer_id = ""
	column = ""
	ebay_item_id = ""
	ebay_order_id = ""
	sales_order = json.loads(sales_order)
	
	if ("ebay_buyer_id" in sales_order):
		buyer_id = sales_order.get("ebay_buyer_id")
		column = "ebay_buyer_id"
		ebay_order_id = sales_order.get("ebay_order_id")
	elif ("ebaytwo_buyer_id" in sales_order ):
		buyer_id = sales_order.get("ebaytwo_buyer_id")
		column = "ebaytwo_buyer_id"
		ebay_order_id = sales_order.get("ebaytwo_order_id")
	ebay_item_id = ebay_order_id.split('-')[0]
	return {"buyer_id": buyer_id, "column": column, "ebay_item_id": ebay_item_id}
