frappe.listview_settings['Vehicle Allocation'] = {
	add_fields: ["is_booked"],
	get_indicator: function (doc) {
		if (doc.is_booked) {
			return [__("Booked"), "green", "is_booked,=,1"];
		} else {
			return [__("Available"), "blue", "is_booked,=,0"];
		}
	},
};
