import webnotes
from webnotes.modules.module_manager import reload_doc
	
def execute():
	"""
		* Reload RV Tax Detail
		* Reload Support Ticket
		* Run Install Print Format Patch
		* Reload DocLayer
	"""
	reload_doc('accounts', 'doctype', 'rv_tax_detail')
	reload_doc('support', 'doctype', 'support_ticket')
	reload_print_formats()
	reload_doc('core', 'doctype', 'doclayer')

def reload_print_formats():
	"""
		Reloads the following print formats:
		* Sales Invoice Classic/Modern/Spartan
		* Sales Order Classic/Modern/Spartan
		* Delivery Note Classic/Modern/Spartan
		* Quotation Classic/Modern/Spartan
	"""
	reload_doc('accounts', 'Print Format', 'Sales Invoice Classic')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Modern')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Spartan')

	reload_doc('selling', 'Print Format', 'Sales Order Classic')
	reload_doc('selling', 'Print Format', 'Sales Order Modern')
	reload_doc('selling', 'Print Format', 'Sales Order Spartan')

	reload_doc('selling', 'Print Format', 'Quotation Classic')
	reload_doc('selling', 'Print Format', 'Quotation Modern')
	reload_doc('selling', 'Print Format', 'Quotation Spartan')

	reload_doc('stock', 'Print Format', 'Delivery Note Classic')
	reload_doc('stock', 'Print Format', 'Delivery Note Modern')
	reload_doc('stock', 'Print Format', 'Delivery Note Spartan')
