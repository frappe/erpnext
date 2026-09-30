// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Period Closing Voucher"] = {
	add_fields: ["gle_processing_status"],
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "red",
			Submitted: "blue",
			Cancelled: "red",
		};

		const gle_processing_status = {
			"In Progress": [__("Processing GL Entries"), "blue"],
			Completed: [__("Period Closed"), "green"],
			Failed: [__("Period Closing Failed"), "red"],
		};
		if (doc.docstatus != 0) {
			return [
				gle_processing_status[doc.gle_processing_status][0],
				gle_processing_status[doc.gle_processing_status][1],
				"gle_processing_status,=," + doc.gle_processing_status,
			];
		}

		return [__(doc.docstatus), status_colors[doc.docstatus], "docstatus,=," + doc.docstatus];
	},
};
