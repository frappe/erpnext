# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

@frappe.whitelist()
def get_feed(limit_start, limit_page_length):
	"""get feed"""
	return frappe.get_list("Feed", fields=["name", "feed_type", "doc_type", "subject", "owner", "modified"],
		limit_start = limit_start, limit_page_length = limit_page_length)
