from frappe.database.utils import drop_index_if_exists


def execute():
	drop_index_if_exists("tabSerial and Batch Entry", "serial_no")
	drop_index_if_exists("tabSerial and Batch Entry", "warehouse")
	drop_index_if_exists("tabSerial and Batch Entry", "type_of_transaction")
