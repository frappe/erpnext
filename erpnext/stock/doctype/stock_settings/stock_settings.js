// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Settings', {
	refresh: function(frm) {
		let filters = function() {
			return {
				filters : {
					is_group : 0
				}
			};
		};

		frm.set_query("default_warehouse", filters);
		frm.set_query("sample_retention_warehouse", filters);
	}
});

frappe.tour['Stock Settings'] = [
	{
		fieldname: "item_naming_by",
		title: __("Item Naming By"),
		description: __("By default, the Item Name is set as per the Item Code entered. If you want Items to be named by a") + " " +
		"<a href='https://docs.erpnext.com/docs/user/manual/en/setting-up/settings/naming-series' target='_blank'>Naming Series</a>" + " " +
		__("choose the 'Naming Series' option."),
	},
	{
		fieldname: "default_warehouse",
		title: __("Default Warehouse"),
		description: __("Set a Default Warehouse for Inventory Transactions. This will be fetched into the Default Warehouse in the Item master.")
	},
	{
		fieldname: "valuation_method",
		title: __("Valuation Method"),
		description: __("Choose between FIFO and Moving Average Valuation Methods. Click") + " " +
		"<a href='https://docs.erpnext.com/docs/user/manual/en/stock/articles/item-valuation-fifo-and-moving-average' target='_blank'>here</a>" + " " +
		__("to know more about them.")
	},
	{
		fieldname: "show_barcode_field",
		title: __("Show Barcode Field"),
		description: __("Show 'Scan Barcode' field above every child table to insert Items with ease.")
	},
	{
		fieldname: "action_if_quality_inspection_is_not_submitted",
		title: __("Action if Quality Inspection Is Not Submitted"),
		description: __("Quality inspection is performed on the inward and outward movement of goods. Receipt and delivery transactions will be stopped or the user will be warned if the quality inspection is not performed.")

	},
	{
		fieldname: "automatically_set_serial_nos_based_on_fifo",
		title: __("Automatically Set Serial Nos based on FIFO"),
		description: __("Serial numbers for stock will be set automatically based on the Items entered based on first in first out in transactions like Purchase/Sales Invoices, Delivery Notes, etc.")
	}
];
