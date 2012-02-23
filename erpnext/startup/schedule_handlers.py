"""will be called by scheduler"""

import webnotes
	
def execute_all():
	"""get support email"""
	from support.doctype.support_ticket import get_support_mails
	get_support_mails()
	
def execute_daily():
	"""email digest"""
	from setup.doctype.email_digest.email_digest import send
	send()