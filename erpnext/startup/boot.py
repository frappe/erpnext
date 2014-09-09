# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import frappe

	bootinfo.custom_css = frappe.db.get_value('Style Settings', None, 'custom_css') or ''
	bootinfo.website_settings = frappe.get_doc('Website Settings')

	if frappe.session['user']!='Guest':
		bootinfo.letter_heads = get_letter_heads()

		update_page_info(bootinfo)

		load_country_and_currency(bootinfo)

		bootinfo.notification_settings = frappe.get_doc("Notification Control",
			"Notification Control")

		# if no company, show a dialog box to create a new company
		bootinfo.customer_count = frappe.db.sql("""select count(*) from tabCustomer""")[0][0]

		if not bootinfo.customer_count:
			bootinfo.setup_complete = frappe.db.sql("""select name from
				tabCompany limit 1""") and 'Yes' or 'No'

		bootinfo.docs += frappe.db.sql("""select name, default_currency, cost_center
            from `tabCompany`""", as_dict=1, update={"doctype":":Company"})

def load_country_and_currency(bootinfo):
	country = frappe.db.get_default("country")
	if country and frappe.db.exists("Country", country):
		bootinfo.docs += [frappe.get_doc("Country", country)]

	bootinfo.docs += frappe.db.sql("""select * from tabCurrency
		where ifnull(enabled,0)=1""", as_dict=1, update={"doctype":":Currency"})

def get_letter_heads():
	import frappe
	ret = frappe.db.sql("""select name, content from `tabLetter Head`
		where ifnull(disabled,0)=0""")
	return dict(ret)

def update_page_info(bootinfo):
	bootinfo.page_info.update({
		"Chart of Accounts": {
			"title": "Chart of Accounts",
			"route": "Accounts Browser/Account"
		},
		"Chart of Cost Centers": {
			"title": "Chart of Cost Centers",
			"route": "Accounts Browser/Cost Center"
		},
		"Item Group Tree": {
			"title": "Item Group Tree",
			"route": "Sales Browser/Item Group"
		},
		"Customer Group Tree": {
			"title": "Customer Group Tree",
			"route": "Sales Browser/Customer Group"
		},
		"Territory Tree": {
			"title": "Territory Tree",
			"route": "Sales Browser/Territory"
		},
		"Sales Person Tree": {
			"title": "Sales Person Tree",
			"route": "Sales Browser/Sales Person"
		}
	})
