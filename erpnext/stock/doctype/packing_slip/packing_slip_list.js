frappe.listview_settings["Packing Slip"] = {
	add_fields: ["name", "status"],
	get_indicator: (doc) => {
		let color;
		if (doc.status == "Delivered") {
			color = "green";
		} else if (doc.status == "In Stock") {
			color = "blue";
		} else if (doc.status == "Nested") {
			color = "light-blue";
		} else if (doc.status == "Unpacked") {
			color = "grey";
		}

		if (color) {
			return [__(doc.status), color, "status,=," + doc.status];
		}
	},
};
