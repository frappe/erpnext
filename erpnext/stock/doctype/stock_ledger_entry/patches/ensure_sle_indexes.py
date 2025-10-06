from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import (
	on_doctype_update as create_sle_indexes,
)


def execute():
	"""Ensure SLE Indexes"""

	create_sle_indexes()
