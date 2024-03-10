// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Subcontracting Order"] = {
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "grey",
			Open: "orange",
			"Partially Received": "yellow",
			Completed: "green",
			"Partial Material Transferred": "purple",
			"Material Transferred": "blue",
<<<<<<< HEAD
			"Closed": "red",
			"Cancelled": "red",
=======
			Closed: "green",
			Cancelled: "red",
>>>>>>> ec74a5e566 (style: format js files)
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
