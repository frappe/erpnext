// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Product Bundle"] = {
	add_fields: ["disabled"],
	get_indicator(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,1"];
		}
		return [__("Active"), "green", "disabled,=,0"];
	},
};
