import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def on_update(self):
		tmp = None
		for d in self.doclist:
			if d.doctype=="Product Group":
				import json
				tmp = json.dumps({"item_group": d.item_group, "label":d.label})
				break
				
		webnotes.conn.set_default("default_product_category", tmp)