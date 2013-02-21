from __future__ import unicode_literals
def execute():
	"""sync supplier quotatoin and create supplier quotation mappers"""
	from webnotes.model.sync import sync
	sync('buying', 'supplier_quotation')
	sync('buying', 'supplier_quotation_item')
	sync('buying', 'purchase_request')
	sync('buying', 'purchase_request_item')
	sync('buying', 'purchase_order')
	sync('buying', 'purchase_order_item')
	
	from webnotes.modules import reload_doc
	reload_doc('buying', 'DocType Mapper', 'Material Request-Supplier Quotation')
	reload_doc('buying', 'DocType Mapper', 'Supplier Quotation-Purchase Order')
	