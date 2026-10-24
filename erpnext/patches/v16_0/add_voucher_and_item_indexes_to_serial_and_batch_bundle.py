from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import on_doctype_update


def execute():
	# on_doctype_update only runs when the DocType itself is re-synced, so existing sites need this.
	on_doctype_update()
