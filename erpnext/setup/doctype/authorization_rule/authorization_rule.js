// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Authorization Rule", {
	setup: function (frm) {
		frm.set_query("system_user", function () {
			return { query: "frappe.core.doctype.user.user.user_query" };
		});

		frm.set_query("approving_user", function () {
			return { query: "frappe.core.doctype.user.user.user_query" };
		});

		frm.set_query("system_role", function () {
			return {
				filters: [["Role", "name", "not in", "Administrator, Guest, All"]],
			};
		});

		frm.set_query("master_name", function () {
			return frm.events.get_master_name_query(frm);
		});

		frm.set_query("to_emp", function () {
			return { query: "erpnext.controllers.queries.employee_query" };
		});
	},
	refresh: function (frm) {
		frm.events.set_master_type(frm);
		unhide_field(["system_role", "system_user", "value"]);
		hide_field(["to_emp", "to_designation"]);
	},
	get_master_name_query: function (frm) {
		if (frm.doc.based_on == "Customerwise Discount") {
			return {
				doctype: "Customer",
				filters: [["Customer", "docstatus", "!=", 2]],
			};
		} else if (frm.doc.based_on == "Itemwise Discount") {
			return {
				doctype: "Item",
				query: "erpnext.controllers.queries.item_query",
			};
		} else if (frm.doc.based_on === "Item Group wise Discount") {
			return {
				doctype: "Item Group",
				filters: {
					is_group: 0,
				},
			};
		} else {
			return {
				filters: [["Item", "name", "=", "cheating done to avoid null"]],
			};
		}
	},
	set_master_type: function (frm) {
		if (frm.doc.based_on === "Customerwise Discount") {
			unhide_field("master_name");
			frm.set_value("customer_or_item", "Customer");
		} else if (frm.doc.based_on === "Itemwise Discount") {
			unhide_field("master_name");
			frm.set_value("customer_or_item", "Item");
		} else if (frm.doc.based_on === "Item Group wise Discount") {
			unhide_field("master_name");
			frm.set_value("customer_or_item", "Item Group");
		} else {
			frm.set_value("customer_or_item", "");
			frm.set_value("master_name", "");
			hide_field("master_name");
		}
	},
	based_on: function (frm) {
		frm.events.set_master_type(frm);
		if (frm.doc.based_on === "Not Applicable") {
			frm.set_value("value", 0);
			hide_field("value");
		} else {
			unhide_field("value");
		}
	},
	transaction: function (frm) {
		unhide_field(["system_role", "system_user", "value", "based_on"]);
		hide_field(["to_emp", "to_designation"]);
	},
});
