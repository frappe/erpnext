"""
	Reload DocLayer, DocLayerField and Print Format doctypes
"""
def execute():
	from webnotes.modules.module_manager import reload_doc
	reload_doc('core', 'doctype', 'print_format')
	reload_doc('core', 'doctype', 'doclayer')
	reload_doc('core', 'doctype', 'doclayerfield')
	reload_doc('accounts', 'doctype', 'gl_entry')
	from webnotes.model.doc import Document
	d = Document('DocType Label')
	d.dt = "DocLayer"
	d.dt_label = "Customize Form View"
	d.save(1)
	from webnotes.session_cache import clear
	clear()
