// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Product Bundle"] = {
	add_fields: ["disabled"],
	get_indicator(doc) {
		if (doc.disabled) {
			return [__("Disabled"), "grey", "disabled,=,1"];
		}
<<<<<<< HEAD
		return [__("Active"), "green", "disabled,=,0"];
=======
		if (doc.docstatus === 1 && doc.is_active) {
			return [__("Active"), "green", "is_active,=,1|disabled,=,0|docstatus,=,1"];
		}
		if (doc.docstatus === 1 && !doc.is_active) {
			return [__("Inactive"), "gray", "is_active,=,0|disabled,=,0|docstatus,=,1"];
		}
>>>>>>> a218b8db8c (fix: submittable product bundle issues)
	},
};
