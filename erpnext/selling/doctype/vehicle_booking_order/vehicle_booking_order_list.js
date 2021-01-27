frappe.listview_settings['Vehicle Booking Order'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if(["To Receive Payment", "To Deposit Payment", "To Receive Vehicle",
				"To Receive Invoice", "To Deliver Vehicle", "To Deliver Invoice",
				"To Assign Allocation", "To Assign Vehicle"].includes(doc.status)) {
			return [__(doc.status), "orange", `status,=,${doc.status}`];
		} else if(["Overdue Payment", "Overdue Delivery"].includes(doc.status)) {
			return [__(doc.status), "red", `status,=,${doc.status}`];
		}
	}
};
