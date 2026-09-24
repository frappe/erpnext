// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = erpnext.get_stock_balance_report_settings();

erpnext.utils.add_inventory_dimensions("Stock Balance", 8);
