import json, webnotes

@webnotes.whitelist(allow_guest=True)
def send(args):
	"""create support ticket"""
	args = json.loads(args)
	
	from webnotes.model.doc import Document
	d = Document('Support Ticket')
	d.raised_by = args['email']
	d.description = 'From: ' + args['name'] + '\n\n' + args['message']
	d.subject = 'Website Query'
	d.status = 'Open'
	d.owner = 'Guest'
	d.save(1)
	webnotes.msgprint("Thank you for your query. We will respond as soon as we can.")