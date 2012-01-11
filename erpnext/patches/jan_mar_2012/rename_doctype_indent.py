import webnotes
def execute():
	"""
		* Create DocType Label
		* Reload Related DocTypes
	"""
	create_doctype_label()
	reload_related_doctype()


def create_doctype_label():
	"""
		Creates a DocType Label Record for Indent
	"""
	res = webnotes.conn.sql("""\
		SELECT name FROM `tabDocType Label`
		WHERE name='Indent'
	""")
	if not(res and res[0] and res[0][0]):
		from webnotes.model.doc import Document
		doclabel = Document('DocType Label')
		doclabel.dt = 'Indent'
		doclabel.dt_label = 'Purchase Requisition'
		doclabel.save(1)


def reload_related_doctype():
	"""
		Reload:
		* indent
		* purchase_order
		* po_detail
	"""
	from webnotes.modules.module_manager import reload_doc
	reload_doc('buying', 'doctype', 'indent')
	reload_doc('buying', 'doctype', 'purchase_order')
	reload_doc('buying', 'doctype', 'po_detail')
