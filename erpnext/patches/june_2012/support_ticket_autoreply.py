from __future__ import unicode_literals
def execute():
	"""New Send Autoreply checkbox in Email Settings"""
	import webnotes
	import webnotes.utils
	
	import webnotes.model.sync
	webnotes.conn.commit()
	webnotes.model.sync.sync('setup', 'email_settings')
	webnotes.conn.begin()
	
	sync_support_mails = webnotes.utils.cint(webnotes.conn.get_value('Email Settings',
							None, 'sync_support_mails'))
							
	if sync_support_mails:
		webnotes.conn.set_value('Email Settings', None, 'send_autoreply', 1)