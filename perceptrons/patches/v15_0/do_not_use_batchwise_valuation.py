import frappe


def execute():
	valuation_method = frappe.db.get_single_value("Stock Settings", "valuation_method")
	if valuation_method in ["FIFO", "LIFO"]:
		return

	if frappe.get_all("Batch", filters={"use_batchwise_valuation": 1}, limit=1):
		return

	if frappe.get_all("Item", filters={"has_batch_no": 1, "valuation_method": "FIFO"}, limit=1):
		return

	frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 1)
