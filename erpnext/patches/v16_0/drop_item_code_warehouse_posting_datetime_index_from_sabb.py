from frappe.database.utils import drop_index_if_exists


def execute():
	drop_index_if_exists("tabSerial and Batch Bundle", "item_code_warehouse_posting_datetime_creation_index")
