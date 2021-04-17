frappe.listview_settings['Vehicle Booking Order'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if(["To Assign Allocation", "To Assign Vehicle"].includes(doc.status)) {
			return [__(doc.status), "purple", `status,=,${doc.status}`];
		} else if (["To Receive Payment", "To Receive Vehicle", "To Receive Invoice"].includes(doc.status)) {
			return [__(doc.status), "yellow", `status,=,${doc.status}`];
		} else if(["To Deposit Payment", "To Deliver Vehicle", "To Deliver Invoice"].includes(doc.status)) {
			return [__(doc.status), "orange", `status,=,${doc.status}`];
		} else if(["Payment Overdue", "Delivery Overdue"].includes(doc.status)) {
			return [__(doc.status), "red", `status,=,${doc.status}`];
		}
	},
	onload: function(listview) {
		listview.page.fields_dict.item_code.get_query = () => erpnext.queries.item({"is_vehicle": 1, "include_in_vehicle_booking": 1});
	}
};
