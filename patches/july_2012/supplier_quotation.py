from __future__ import unicode_literals
import webnotes

def execute():
	"""sync supplier quotatoin and create supplier quotation mappers"""
	webnotes.reload_doc('buying', 'doctype', 'supplier_quotation')
	webnotes.reload_doc('buying', 'doctype', 'supplier_quotation_item')
	webnotes.reload_doc('buying', 'doctype', 'purchase_order')
	webnotes.reload_doc('buying', 'doctype', 'purchase_order_item')
	
	from webnotes.modules import reload_doc
	reload_doc('buying', 'DocType Mapper', 'Material Request-Supplier Quotation')
	reload_doc('buying', 'DocType Mapper', 'Supplier Quotation-Purchase Order')
	