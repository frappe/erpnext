import webnotes
from webnotes.utils import cint

class DocType:
	def __init__(self,dt,dn):
		self.doc, self.doctype = dt,dn
		
	def on_update(self):
		"""
			Sets or cancels the event in the scheduler
		"""
		if cint(self.doc.integrate_incoming):
			from webnotes.utils.scheduler import set_event
			set_event('maintenance.doctype.support_ticket.get_support_mails', 60*5, 1)
		else:
			from webnotes.utils.scheduler import cancel_event
			cancel_event('maintenance.doctype.support_ticket.get_support_mails')
			