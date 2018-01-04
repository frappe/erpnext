# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import utils

class POSCashierClosing(Document):
		pass

@frappe.whitelist()
def get_pos_sales_total(from_date,to_date,from_time,to_time,owner):
	return frappe.db.sql("""select sum(paid_amount) from `tabSales Invoice` where docstatus !=2 and is_pos =1 and posting_date >= %s and posting_date <= %s and posting_time >= %s and posting_time <= %s and owner = %s""", (from_date,to_date,from_time,to_time,owner))[0][0] or 0

@frappe.whitelist()
def get_last_POS_Closing():
	return frappe.get_all('POS Cashier Closing',fields=["name"],filters={"owner":frappe.session.user,"docstatus":0,"start_date":utils.today()},order_by='modified DESC', limit=1)

@frappe.whitelist()
def check_POS_duplicate(doc_name,start_date,shift,owner):
	return frappe.db.sql("""select count(*) from `tabPOS Cashier Closing` where docstatus !=2 and start_date = %s and shift=%s and user = %s and name!=%s""", (start_date,shift,owner,doc_name))[0][0] or 0
