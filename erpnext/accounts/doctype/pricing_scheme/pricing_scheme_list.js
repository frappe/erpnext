// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.listview_settings["Pricing Scheme"] = {
	add_fields: ["disabled", "valid_from", "valid_upto"],

	get_indicator(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "gray", "disabled,=,1"];
		}
		const now = frappe.datetime.now_datetime();
		if (doc.valid_from && doc.valid_from > now) {
			return [__("Upcoming"), "orange", "valid_from,>,Now"];
		}
		if (doc.valid_upto && doc.valid_upto < now) {
			return [__("Expired"), "red", "valid_upto,<,Now"];
		}
		return [__("Active"), "green", "disabled,=,0"];
	},
};
