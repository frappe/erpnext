class DocType:
	def __init__(self, d, dl=[]):
		self.doc, self.doclist = d, dl
		
	def rename(self):
		"""
		Generate update quereies for rename
		"""
		import webnotes.model
		from webnotes.model.code import get_obj
		
		# call on_rename method if exists
		obj = get_obj(self.doc.select_doctype, self.doc.document_to_rename)
		if hasattr(obj, 'on_rename'):
			obj.on_rename(self.doc.new_name,self.doc.document_to_rename)
			
		# rename the document		
		webnotes.model.rename(self.doc.select_doctype, self.doc.document_to_rename, self.doc.new_name)
		
		webnotes.msgprint("Successfully renamed "+self.doc.select_doctype+" : '"+self.doc.document_to_rename+"' to <b>"+self.doc.new_name+"</b>")
