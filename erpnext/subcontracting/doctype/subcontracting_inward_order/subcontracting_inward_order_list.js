// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Subcontracting Inward Order"] = {
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "red",
			Open: "orange",
			Ongoing: "yellow",
			Produced: "blue",
			Delivered: "green",
			Closed: "grey",
			Cancelled: "red",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
