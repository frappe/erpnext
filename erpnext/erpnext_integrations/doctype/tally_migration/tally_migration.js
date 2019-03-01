// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tally Migration', {
	refresh: function(frm) {
		if (frm.doc.master_data && frm.doc.day_book) {
			frm.disable_save();
			if(frm.doc.status != "In Progress") {
				frm.page.set_primary_action("Preprocess", () => frm.trigger("preprocess"));
			}
		} else {
			frm.set_value("status", "Attach File");
		}
		if (frm.doc.tally_company && frm.doc.erpnext_company) {
			frm.set_df_property("company_section", "hidden", 0);
			frm.page.set_primary_action("Start Import", () => frm.trigger("start_import"));
		}
	},
	preprocess: function(frm) {
		frm.call({
			doc: frm.doc,
			method: "preprocess",
			freeze: true
		}).then((r) => {
			frm.set_value("status", "Preprocessing In Progress");
		});
	},
	start_import: function(frm) {
		frm.call({
			doc: frm.doc,
			method: "start_import",
			freeze: true
		}).then((r) => {
			frm.set_value("status", "Import In Progress");
		});
	},
});
