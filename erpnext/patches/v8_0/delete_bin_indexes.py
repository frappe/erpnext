# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe

def execute():
	# delete bin indexes
	unwanted_indexes = ["item_code", "warehouse"]

	for k in unwanted_indexes:
		try:
			frappe.db.sql("drop index {0} on `tabBin`".format(k))
		except:
			pass