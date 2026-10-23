// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Engineering Design"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Draft: "red",
			Approved: "blue",
			Completed: "green",
			Superseded: "gray",
			Cancelled: "red",
		};
		return [__(doc.status), colors[doc.status], `status,=,${doc.status}`];
	},
};
