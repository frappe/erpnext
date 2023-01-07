frappe.listview_settings["Handling Unit"] = {
	add_fields: ["name", "customer_name", "status"],
	get_indicator: (doc) => {
		let color;
		if (doc.status == "Delivered") {
			color = "grey";
		} else if (doc.status == "In Stock") {
			color = "blue";
		} else if (doc.status == "Repacked") {
			color = "light-blue";
		} else if (doc.status == "Inactive") {
			color = "grey";
		}

		return [__(doc.status), color, "status,=," + doc.status];
	},
};
