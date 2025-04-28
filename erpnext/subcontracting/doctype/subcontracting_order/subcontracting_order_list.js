// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Subcontracting Order"] = {
	get_indicator: function (doc) {
		const status_colors = {
<<<<<<< HEAD
			Draft: "red",
=======
			Draft: "grey",
>>>>>>> 7c4cf3e834 (Favicon.svg)
			Open: "orange",
			"Partially Received": "yellow",
			Completed: "green",
			"Partial Material Transferred": "purple",
			"Material Transferred": "blue",
			Closed: "green",
			Cancelled: "red",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
