import webnotes
def subscribe(arg):
	"""subscribe to blog (blog_subscriber)"""
	if webnotes.conn.sql("""select name from `tabBlog Subscriber` where name=%s""", arg):
		webnotes.msgprint("Already a subscriber. Thanks!")
	else:
		from webnotes.model.doc import Document
		d = Document('Blog Subscriber')
		d.name = arg
		d.save()
		webnotes.msgprint("Thank you for subscribing!")