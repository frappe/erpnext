# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    frappe.db.sql(''' update `TabSales Order` set status='To Bill' where order_type='Maintenance' and status='To Deliver and Bill' ''')