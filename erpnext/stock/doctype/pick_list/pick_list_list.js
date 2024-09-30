// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Pick List"] = {
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "grey",
			Open: "orange",
			Completed: "green",
			Cancelled: "red",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
