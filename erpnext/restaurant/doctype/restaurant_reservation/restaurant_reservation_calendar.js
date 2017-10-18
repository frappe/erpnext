frappe.views.calendar["Restaurant Reservation"] = {
	field_map: {
		"start": "reservation_time",
		"end": "reservation_end_time",
		"id": "name",
		"title": "customer_name",
		"allDay": "allDay",
	},
	gantt: true,
	filters: [
		{
			"fieldtype": "Data",
			"fieldname": "customer_name",
			"label": __("Customer Name")
		}
	],
	get_events_method: "erpnext.restaurant.doctype.restaurant_reservation.restaurant_reservation.get_events"
};
