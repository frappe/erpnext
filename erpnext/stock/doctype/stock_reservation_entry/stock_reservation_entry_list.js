// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Stock Reservation Entry"] = {
	filters: [["status", "!=", "Cancelled"]],
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "red",
			"Partially Reserved": "orange",
			Reserved: "blue",
			"Partially Delivered": "purple",
			Delivered: "green",
			Cancelled: "red",
		};

		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
