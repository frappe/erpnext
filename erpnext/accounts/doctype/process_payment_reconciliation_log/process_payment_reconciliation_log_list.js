frappe.listview_settings["Process Payment Reconciliation Log"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		var colors = {
			"Partially Reconciled": "orange",
			Paused: "orange",
			Reconciled: "green",
			Failed: "red",
			Cancelled: "red",
			Running: "blue",
		};
		let status = doc.status;
		return [__(status), colors[status], "status,=," + status];
	},
};
