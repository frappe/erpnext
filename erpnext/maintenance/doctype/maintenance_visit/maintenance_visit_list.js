frappe.listview_settings["Maintenance Visit"] = {
	add_fields: ["customer", "customer_name", "completion_status", "maintenance_type"],
	get_indicator: function (doc) {
		var s = doc.completion_status || "Pending";
		return [
			__(s),
			{
				Pending: "blue",
				"Partially Completed": "orange",
				"Fully Completed": "green",
			}[s],
			"completion_status,=," + doc.completion_status,
		];
	},
};
