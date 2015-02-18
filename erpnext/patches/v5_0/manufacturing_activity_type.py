# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	if not frappe.db.exists('Activity Type','Manufacturing') {
		doc = frappe.new_doc('Activity Type')
		doc.update({
			'activity_type' : 'Manufacturing'
		})
		doc.save()
	}