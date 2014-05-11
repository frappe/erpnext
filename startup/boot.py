# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


from __future__ import unicode_literals
import webnotes
import home

def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import webnotes
	import webnotes.model.doc
	
	bootinfo['custom_css'] = webnotes.conn.get_value('Style Settings', None, 'custom_css') or ''
	bootinfo['website_settings'] = webnotes.model.doc.getsingle('Website Settings')

	if webnotes.session['user']!='Guest':
		bootinfo['letter_heads'] = get_letter_heads()
		
		load_country_and_currency(bootinfo)
		
		import webnotes.model.doctype
		bootinfo['notification_settings'] = webnotes.doc("Notification Control", 
			"Notification Control").get_values()
				
		# if no company, show a dialog box to create a new company
		bootinfo["customer_count"] = webnotes.conn.sql("""select count(*) from tabCustomer""")[0][0]

		if not bootinfo["customer_count"]:
			bootinfo['setup_complete'] = webnotes.conn.sql("""select name from 
				tabCompany limit 1""") and 'Yes' or 'No'
		
		
		# load subscription info
		from webnotes import conf
		for key in ['max_users', 'expires_on', 'max_space', 'status', 'commercial_support']:
			if key in conf: bootinfo[key] = conf.get(key)

		bootinfo['docs'] += webnotes.conn.sql("""select name, default_currency, cost_center
            from `tabCompany`""", as_dict=1, update={"doctype":":Company"})

def load_country_and_currency(bootinfo):
	if bootinfo.control_panel.country and \
		webnotes.conn.exists("Country", bootinfo.control_panel.country):
		bootinfo["docs"] += [webnotes.doc("Country", bootinfo.control_panel.country)]
		
	bootinfo["docs"] += webnotes.conn.sql("""select * from tabCurrency
		where ifnull(enabled,0)=1""", as_dict=1, update={"doctype":":Currency"})

def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)
	
