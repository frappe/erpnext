// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("frappe.interaction_settings");

frappe.interaction_settings["Call"] = {
	field_map : {
		"interaction_type": "doctype",
		"summary": "subject",
		"description": "description",
		"due_date": "start_datetime",
		"reference_doctype": "reference_doctype",
		"reference_document": "reference_document"
	},
	reqd_fields: ["summary", "due_date"],
	hidden_fields: ["public"]
};