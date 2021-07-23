frappe.listview_settings['Delivery Planning'] = {
//	add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date",
//		"per_delivered", "per_billed", "status", "order_type", "name", "skip_delivery_note"],
	hide_name_column: true,
	get_indicator: function (doc) {
		if (doc.d_status === "Pending Planning") {
			// Pending Planning
			return [__("Pending Planning"), "orange", "status,=,Pending Planning"];
		}
		else if (doc.d_status === "Partially Planned") {
			// Partially Planned
			return [__("Partially Planned"), "orange", "status,=,Partially Planned"];
		}
		else if (doc.d_status === "Planned and To Deliver & Order") {
			return [__("Planned and To Deliver & Order"), "yellow", "status,=,Planned and To Deliver & Order"];
		}
		else if (doc.d_status === "To Order") {
			return [__("To Order"), "green", "status,=,To Order"];
		}
		else if (doc.d_status === "To Deliver") {
			return [__("To Deliver"), "green", "status,=,To Deliver"];
		}
		else if (doc.d_status === "Completed") {
			return [__("Completed"), "blue", "status,=,Completed"];
		}
	
	},
};

//Pending Planning
//Partially Planned
//Planned and To Deliver & Order
//To Order
//To Deliver
//Completed
