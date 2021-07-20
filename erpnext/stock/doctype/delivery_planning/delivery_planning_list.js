frappe.listview_settings['Sales Order'] = {
//	add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date",
//		"per_delivered", "per_billed", "status", "order_type", "name", "skip_delivery_note"],
	get_indicator: function (doc) {
		if (doc.d_status === "Pending Planning") {
			// Closed
			return [__("Pending Planning"), "orange", "d_status,=,Pending Planning"];
		}
		else if (doc.d_status === "Partially Planned") {
			// on hold
			return [__("Partially Planned"), "orange", "d_status,=,Partially Planned"];
		}
		else if (doc.d_status === "Planned and To Deliver & Order") {
			return [__("Planned and To Deliver & Order"), "green", "d_status,=,Planned and To Deliver & Order"];
		}
		else if (doc.d_status === "To Order") {
			return [__("To Order"), "green", "d_status,=,To Order"];
		}
		else if (doc.d_status === "To Deliver") {
			return [__("To Deliver"), "green", "d_status,=,To Deliver"];
		}
		else if (doc.d_status === "Completed") {
			return [__("Completed"), "green", "d_status,=,Completed"];
		}
	},
};


//Pending Planning
//Partially Planned
//Planned and To Deliver & Order
//To Order
//To Deliver
//Completed
