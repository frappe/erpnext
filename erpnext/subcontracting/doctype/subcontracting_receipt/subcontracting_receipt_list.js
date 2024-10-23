// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Subcontracting Receipt"] = {
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "grey",
			Return: "gray",
			"Return Issued": "grey",
			Completed: "green",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
