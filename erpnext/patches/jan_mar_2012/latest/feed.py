import webnotes
from webnotes.model.doc import Document
from webnotes.modules import reload_doc

def execute():
	reload_doc('home', 'doctype', 'feed')