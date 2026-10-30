frappe.listview_settings["Customer"] = {
	add_fields: [
		"customer_name",
		"territory",
		"customer_group",
		"customer_type",
		"image",
		"on_hold",
		"release_date",
	],
	get_indicator: function (doc) {
		const is_hold_active = !doc.release_date || doc.release_date >= frappe.datetime.get_today();
		if (!cint(doc.disabled) && cint(doc.on_hold) && is_hold_active) {
			return [__("On Hold"), "red", "on_hold,=,1"];
		}
	},
};
