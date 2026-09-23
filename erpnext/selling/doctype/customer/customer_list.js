frappe.listview_settings["Customer"] = {
	add_fields: ["customer_name", "territory", "customer_group", "customer_type", "image", "on_hold"],
	get_indicator: function (doc) {
		if (!cint(doc.disabled) && cint(doc.on_hold)) {
			return [__("On Hold"), "red", "on_hold,=,1"];
		}
	},
};
