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
<<<<<<< HEAD
			name: 'Warehouse Capacity Summary',
			report_type: 'Page',
			route: 'warehouse-capacity-summary'
		}
	]
=======
			name: "Warehouse Capacity Summary",
			route: "/app/warehouse-capacity-summary",
		},
	],
>>>>>>> ec74a5e566 (style: format js files)
};
