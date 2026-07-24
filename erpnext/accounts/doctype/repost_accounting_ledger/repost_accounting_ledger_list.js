frappe.listview_settings["Repost Accounting Ledger"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		const status_color = {
			Queued: "yellow",
			"In Progress": "blue",
			"Partially Reposted": "orange",
			Completed: "green",
			Failed: "red",
		};
		const color = status_color[doc.status] || "gray";
		return [__(doc.status || "Draft"), color, "status,=," + doc.status];
	},
};
