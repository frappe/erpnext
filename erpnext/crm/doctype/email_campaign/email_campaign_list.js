frappe.listview_settings["Email Campaign"] = {
	get_indicator: function (doc) {
		var colors = {
			Unsubscribed: "red",
			Scheduled: "blue",
			"In Progress": "orange",
			Completed: "green",
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},
};
