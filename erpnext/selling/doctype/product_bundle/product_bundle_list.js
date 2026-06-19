// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Product Bundle"] = {
	add_fields: ["is_active", "disabled"],
	get_indicator(doc) {
		// Draft and Cancelled fall through to the standard docstatus indicators;
		// this only refines submitted bundles.
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,1"];
		}
		if (doc.docstatus === 1 && doc.is_active) {
			return [__("Active"), "green", "is_active,=,1|disabled,=,0|docstatus,=,1"];
		}
		// inactive submitted versions keep the default "Submitted" indicator
	},
};
