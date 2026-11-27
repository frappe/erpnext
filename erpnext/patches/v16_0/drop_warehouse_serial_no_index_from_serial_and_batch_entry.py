from frappe.database.utils import drop_index_if_exists


def execute():
	drop_index_if_exists("tabSerial and Batch Entry", "warehouse_serial_no_posting_datetime_index")
