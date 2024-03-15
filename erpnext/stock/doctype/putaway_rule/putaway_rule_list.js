frappe.listview_settings["Putaway Rule"] = {
	add_fields: ["disable"],
	get_indicator: (doc) => {
		if (doc.disable) {
			return [__("Disabled"), "darkgrey", "disable,=,1"];
		} else {
			return [__("Active"), "blue", "disable,=,0"];
		}
	},

	reports: [
		{
			name: "Warehouse Capacity Summary",
			route: "/app/warehouse-capacity-summary",
		},
	],
};
