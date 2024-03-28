// Copyright (c) 2016, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("List of Contacts", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Import Contacts"),
				function () {
					frappe.prompt(
						{
							fieldtype: "Select",
							options: frm.doc.__onload.import_types,
							label: __("Import Contacts From"),
							fieldname: "doctype",
							reqd: 1,
						},
						function (data) {
							frappe.call({
								method: "erpnext.crm.doctype.list_of_contacts.list_of_contacts.import_from",
								args: {
									name: frm.doc.name,
									doctype: data.doctype,
								},
								callback: function (r) {
									frm.set_value("total_members", r.message);
								},
							});
						},
						__("Import Contacts"),
						__("Import")
					);
				},
				__("Action")
			);

			frm.add_custom_button(
				__("Add Contacts"),
				function () {
					frappe.prompt(
						{
							fieldtype: "Text",
							label: __("Contacts"),
							fieldname: "contact_list",
							reqd: 1,
						},
						function (data) {
							frappe.call({
								method: "erpnext.crm.doctype.list_of_contacts.list_of_contacts.add_contacts",
								args: {
									name: frm.doc.name,
									email_list: data.contact_list,
								},
								callback: function (r) {
									frm.set_value("total_members", r.message);
								},
							});
						},
						__("Add Contacts"),
						__("Add")
					);
				},
				__("Action")
			);
		}
	},
});
