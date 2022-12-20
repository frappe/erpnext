# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DHIGCOAMapper(Document):
	pass

@frappe.whitelist()
def filter_account(doctype, txt, searchfield, start, page_len, filters):
	query = """
		SELECT 
			dg.account_code,
			dg.account_name,
			dg.account_type
		FROM `tabDHI GCOA` dg 
		WHERE NOT EXISTS(
			SELECT 1 FROM 
			`tabDHI GCOA Mapper` dgm
			WHERE dg.account_code = dgm.account_code
		)
		
	"""
	return frappe.db.sql(query)
