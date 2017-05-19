# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	"""Create domain documents"""

    if not frappe.db.exists({'doctype': 'Domain', 'domain': 'Distribution')}):
		doc = frappe.new_doc("Domain")
		doc.domain = "Distribution"
		doc.save()

    if not frappe.db.exists({'doctype': 'Domain', 'domain': 'Manufacturing')}):
		doc = frappe.new_doc("Domain")
		doc.domain = "Manufacturing"
		doc.save()

    if not frappe.db.exists({'doctype': 'Domain', 'domain': 'Retail')}):
		doc = frappe.new_doc("Domain")
		doc.domain = "Retail"
		doc.save()

    if not frappe.db.exists({'doctype': 'Domain', 'domain': 'Services')}):
		doc = frappe.new_doc("Domain")
		doc.domain = "Services"
		doc.save()

    if not frappe.db.exists({'doctype': 'Domain', 'domain': 'Education')}):
		doc = frappe.new_doc("Domain")
		doc.domain = "Education"
		doc.save()