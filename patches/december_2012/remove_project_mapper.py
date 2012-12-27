import webnotes

def execute():
	from webnotes.model import delete_doc
	for d in ["Project-Sales Order", "Project-Delivery Note", "Project-Sales Invoice"]:
		delete_doc("DocType Mapper", d)