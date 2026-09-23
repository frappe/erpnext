frappe.query_reports["Serial and Batch Wise Stock Balance"] = {
	...erpnext.get_stock_balance_report_settings(),
	initial_depth: 0,
};

erpnext.utils.add_inventory_dimensions("Serial and Batch Wise Stock Balance", 8);
