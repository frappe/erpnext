from __future__ import unicode_literals
import frappe

def execute():
	woocommerce_setting_enable_sync = frappe.db.sql("SELECT t.value FROM tabSingles t WHERE doctype = 'Woocommerce Settings' AND field = 'enable_sync'",  as_dict=True)
	if len(woocommerce_setting_enable_sync) and woocommerce_setting_enable_sync[0].value == '1':
		frappe.db.sql("""UPDATE tabSingles
					SET value = (SELECT t.value FROM tabSingles t WHERE doctype = 'Woocommerce Settings' AND field = 'modified_by')
					WHERE doctype = 'Woocommerce Settings'
					AND field = 'creation_user';""")