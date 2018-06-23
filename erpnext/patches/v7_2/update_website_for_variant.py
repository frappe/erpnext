import frappe

def execute():
	# variant must have show_in_website = 0
	frappe.reload_doctype('Item')
	frappe.db.sql('''
		update tabItem set
			show_variant_in_website = 1,
			show_in_website = 0
		where
			show_in_website=1
			and ifnull(variant_of, "")!=""''')