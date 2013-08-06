# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	"""New Send Autoreply checkbox in Email Settings"""
	import webnotes
	import webnotes.utils
	
	webnotes.conn.commit()
	webnotes.reload_doc('setup', 'doctype', 'email_settings')
	webnotes.conn.begin()
	
	sync_support_mails = webnotes.utils.cint(webnotes.conn.get_value('Email Settings',
							None, 'sync_support_mails'))
							
	if sync_support_mails:
		webnotes.conn.set_value('Email Settings', None, 'send_autoreply', 1)