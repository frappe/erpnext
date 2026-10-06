// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.listview_settings["Investment"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Draft: "red",
			"Pending Approval": "orange",
			Rejected: "red",
			Active: "green",
			"Partially Redeemed": "yellow",
			Matured: "blue",
			Redeemed: "gray",
			Cancelled: "red",
		};
		return [__(doc.status), colors[doc.status], `status,=,${doc.status}`];
	},
};
