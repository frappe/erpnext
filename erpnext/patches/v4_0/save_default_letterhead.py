# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	"""save default letterhead to set default_letter_head_content"""
	try:
		letter_head = frappe.get_doc("Letter Head", {"is_default": 1})
		letter_head.save()
	except frappe.DoesNotExistError:
		pass
