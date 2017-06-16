# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	"""Create domain documents"""

	for domain in ("Distribution", "Manufacturing", "Retail", "Services", "Education"):
		if not frappe.db.exists({'doctype': 'Domain', 'domain': domain}):
			doc = frappe.new_doc("Domain")
			doc.domain = "Distribution"
			doc.save()
