# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PartyType(Document):
	pass

@frappe.whitelist()
def get_party_type(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name from `tabParty Type`
			where `{key}` LIKE %(txt)s
			order by name limit %(start)s, %(page_len)s"""
			.format(key=searchfield), {
				'txt': "%%%s%%" % frappe.db.escape(txt),
				'start': start, 'page_len': page_len
			})
