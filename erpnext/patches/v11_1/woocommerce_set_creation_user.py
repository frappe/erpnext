from __future__ import unicode_literals
import frappe

def execute():
	woocommerce_setting_enable_sync = frappe.db.sql("""SELECT t.value
		FROM tabSingles t
		WHERE doctype = 'Woocommerce Settings'
		AND field = 'enable_sync'""", as_dict=True)
	if len(woocommerce_setting_enable_sync) and woocommerce_setting_enable_sync[0].value == '1':
		modified_by = frappe.db.sql("""SELECT t.value
			FROM tabSingles t
			WHERE doctype = 'Woocommerce Settings'
			AND field = 'modified_by'""")
		if len(modified_by):
			modified_by = modified_by[0][0]
			frappe.db.sql("""UPDATE tabSingles
				SET value = %s
				WHERE doctype = 'Woocommerce Settings'
				AND field = 'creation_user';""", (modified_by))