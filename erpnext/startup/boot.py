# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import frappe
	import frappe.model.doc
	
	bootinfo['custom_css'] = frappe.conn.get_value('Style Settings', None, 'custom_css') or ''
	bootinfo['website_settings'] = frappe.model.doc.getsingle('Website Settings')

	if frappe.session['user']!='Guest':
		bootinfo['letter_heads'] = get_letter_heads()
		
		load_country_and_currency(bootinfo)
		
		import frappe.model.doctype
		bootinfo['notification_settings'] = frappe.doc("Notification Control", 
			"Notification Control").get_values()
				
		# if no company, show a dialog box to create a new company
		bootinfo["customer_count"] = frappe.conn.sql("""select count(*) from tabCustomer""")[0][0]

		if not bootinfo["customer_count"]:
			bootinfo['setup_complete'] = frappe.conn.sql("""select name from 
				tabCompany limit 1""") and 'Yes' or 'No'
		
		
		# load subscription info
		from frappe import conf
		for key in ['max_users', 'expires_on', 'max_space', 'status', 'commercial_support']:
			if key in conf: bootinfo[key] = conf.get(key)

		bootinfo['docs'] += frappe.conn.sql("""select name, default_currency, cost_center
            from `tabCompany`""", as_dict=1, update={"doctype":":Company"})

def load_country_and_currency(bootinfo):
	if bootinfo.control_panel.country and \
		frappe.conn.exists("Country", bootinfo.control_panel.country):
		bootinfo["docs"] += [frappe.doc("Country", bootinfo.control_panel.country)]
		
	bootinfo["docs"] += frappe.conn.sql("""select * from tabCurrency
		where ifnull(enabled,0)=1""", as_dict=1, update={"doctype":":Currency"})

def get_letter_heads():
	import frappe
	ret = frappe.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)
	
