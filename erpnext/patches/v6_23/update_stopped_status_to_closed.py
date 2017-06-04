# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for dt in ("Sales Order", "Purchase Order"):
		frappe.db.sql("update `tab{0}` set status='Closed' where status='Stopped'".format(dt))