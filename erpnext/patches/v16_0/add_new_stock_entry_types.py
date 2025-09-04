import frappe


def execute():
	for stock_entry_type in [
		"Receive from Customer",
		"Return Raw Material to Customer",
		"Subcontracting Delivery",
		"Subcontracting Return",
	]:
		frappe.new_doc("Stock Entry Type", purpose=stock_entry_type, is_standard=1).insert(
			ignore_permissions=True
		)
