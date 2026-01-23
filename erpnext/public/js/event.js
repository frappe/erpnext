// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt
frappe.provide("frappe.desk");

frappe.ui.form.on("Event", {
	refresh: function (frm) {
		frm.set_query("reference_doctype", "event_participants", function () {
			return {
				filters: {
					name: ["in", ["Contact", "Lead", "Customer", "Supplier", "Employee", "Sales Partner"]],
				},
			};
		});

		frm.add_custom_button(
			__("Add Leads"),
			function () {
				new frappe.desk.eventParticipants(frm, "Lead");
			},
			__("Add Participants")
		);

		frm.add_custom_button(
			__("Add Customers"),
			function () {
				new frappe.desk.eventParticipants(frm, "Customer");
			},
			__("Add Participants")
		);

		frm.add_custom_button(
			__("Add Suppliers"),
			function () {
				new frappe.desk.eventParticipants(frm, "Supplier");
			},
			__("Add Participants")
		);

		frm.add_custom_button(
			__("Add Employees"),
			function () {
				new frappe.desk.eventParticipants(frm, "Employee");
			},
			__("Add Participants")
		);

		frm.add_custom_button(
			__("Add Sales Partners"),
			function () {
				new frappe.desk.eventParticipants(frm, "Sales Partner");
			},
			__("Add Participants")
		);
	},
});
