from erpnext.stock.doctype.item.item_search import ItemSearch


def execute():
	"""Indexes built before the current folding hold unfolded text. Drop them, and any unfinished
	build, which the scheduler would otherwise resume as is."""
	for db_name in ("item_search.db", "item_search.temp.db"):
		ItemSearch(db_name).drop_index()
