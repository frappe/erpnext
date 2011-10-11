class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_trash(self):
		import webnotes
		webnotes.conn.sql("delete from tabAnswer where question=%s", self.doc.name)
		