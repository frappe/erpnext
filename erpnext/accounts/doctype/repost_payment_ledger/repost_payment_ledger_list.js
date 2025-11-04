frappe.listview_settings["Repost Payment Ledger"] = {
	add_fields: ["repost_status"],
	get_indicator: function (doc) {
		var colors = {
			Queued: "orange",
			Completed: "green",
			Failed: "red",
		};
		let status = doc.repost_status;
		return [__(status), colors[status], "status,=," + status];
	},
};
