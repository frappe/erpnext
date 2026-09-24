frappe.query_reports["Serial and Batch Wise Stock Balance"] = {
	...erpnext.get_stock_balance_report_settings(),
	initial_depth: 0,

	after_datatable_render: function () {
		const filters = frappe.query_report.get_values();

		frappe
			.xcall(
				"erpnext.stock.report.serial_and_batch_wise_stock_balance.serial_and_batch_wise_stock_balance.has_stock_closing_entry_before",
				{ company: filters.company, from_date: filters.from_date }
			)
			.then((has_closing_entry) => {
				if (has_closing_entry) {
					frappe.show_alert({
						message: __(
							"Stock Closing Entry is ignored in this report. Balances are computed from the full stock ledger."
						),
						indicator: "orange",
					});
				}
			});
	},
};

erpnext.utils.add_inventory_dimensions("Serial and Batch Wise Stock Balance", 8);
