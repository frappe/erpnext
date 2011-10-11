import webnotes
sql = webnotes.conn.sql
	
from webnotes.utils import cint, cstr

class DocType:
	def __init__(self,doc,doclist):
		self.doc,self.doclist = doc,doclist

	def set_vals(self):
		res = sql("select field, value from `tabSingles` where doctype = 'Control Panel' and field IN ('outgoing_mail_server','mail_login','mail_password','auto_email_id','mail_port','use_ssl')")
		ret = {}
		for r in res:
			ret[cstr(r[0])]=r[1] and cstr(r[1]) or ''
				
		return ret

	def set_cp_value(self, key):
		"""
			Update value in control panel
		"""
		if self.doc.fields.get(key):
			webnotes.conn.set_value('Control Panel', None, key, self.doc.fields[key])
		
	def on_update(self):
		"""
			Sets or cancels the event in the scheduler
		"""
		# update control panel
		for f in ('outgoing_mail_server', 'mail_login', 'mail_password', 'auto_email_id', 'mail_port', 'use_ssl'):
			self.set_cp_value(f)

		# setup scheduler for support emails
		if cint(self.doc.sync_support_mails):
			if not (self.doc.support_host and self.doc.support_username and self.doc.support_password):
				webnotes.msgprint("You must give the incoming POP3 settings for support emails to activiate mailbox integration", raise_exception=1)
			
			from webnotes.utils.scheduler import set_event
			set_event('support.doctype.support_ticket.get_support_mails', 60*5, 1)
		else:
			from webnotes.utils.scheduler import cancel_event
			cancel_event('support.doctype.support_ticket.get_support_mails')