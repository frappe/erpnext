frappe.listview_settings["Repost Accounting Ledger"] = {
	add_fields: ["status"],
	// drafts and cancelled documents are coloured by the framework before it gets here
	get_indicator: function (doc) {
		if (!doc.status) return;

		const status_color = {
			Queued: "yellow",
			"In Progress": "blue",
			"Partially Reposted": "orange",
			Completed: "green",
			Failed: "red",
		};
		return [__(doc.status), status_color[doc.status] || "gray", "status,=," + doc.status];
	},
};
