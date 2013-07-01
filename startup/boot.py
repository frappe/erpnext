# ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
# GNU General Public License. See "license.txt"


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

		import webnotes.model.doctype
		bootinfo['notification_settings'] = webnotes.doc("Notification Control", 
			"Notification Control").get_values()
				
		# if no company, show a dialog box to create a new company
		bootinfo["customer_count"] = webnotes.conn.sql("""select count(*) from tabCustomer""")[0][0]

		if not bootinfo["customer_count"]:
			bootinfo['setup_complete'] = webnotes.conn.sql("""select name from 
				tabCompany limit 1""") and 'Yes' or 'No'
		
		
		# load subscription info
		import conf
		for key in ['max_users', 'expires_on', 'max_space', 'status', 'developer_mode']:
			if hasattr(conf, key): bootinfo[key] = getattr(conf, key)

		bootinfo['docs'] += webnotes.conn.sql("""select name, default_currency, cost_center
            from `tabCompany`""", as_dict=1, update={"doctype":":Company"})
			
def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)
	