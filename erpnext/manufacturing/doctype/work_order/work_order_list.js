frappe.listview_settings["Work Order"] = {
	add_fields: [
		"bom_no",
		"status",
		"sales_order",
		"qty",
		"produced_qty",
		"expected_delivery_date",
		"planned_start_date",
		"planned_end_date",
	],
	filters: [["status", "!=", "Stopped"]],
	get_indicator: function (doc) {
		if (doc.status === "Submitted") {
			return [__("Not Started"), "orange", "status,=,Submitted"];
		} else {
			return [
				__(doc.status),
				{
					Draft: "red",
					Stopped: "red",
					"Not Started": "red",
					"In Process": "orange",
					Completed: "green",
<<<<<<< HEAD
					"Stock Reserved": "blue",
					"Stock Partially Reserved": "orange",
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
					Cancelled: "gray",
				}[doc.status],
				"status,=," + doc.status,
			];
		}
	},
};
