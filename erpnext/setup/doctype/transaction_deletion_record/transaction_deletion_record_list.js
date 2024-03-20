// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Transaction Deletion Record"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		let colors = {
			Queued: "orange",
			Completed: "green",
			Running: "blue",
			Failed: "red",
		};
		let status = doc.status;
		return [__(status), colors[status], "status,=," + status];
	},
};
