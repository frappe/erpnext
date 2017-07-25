# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_default_records
def execute():
	frappe.reload_doc('buying', 'doctype', 'supplier_scorecard_variable')
	frappe.reload_doc('buying', 'doctype', 'supplier_scorecard_standing')
	make_default_records()