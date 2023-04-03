// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.ui.form.on("Rename Tool", {
	onload: function(frm) {
		return frappe.call({
			method: "erpnext.utilities.doctype.rename_tool.rename_tool.get_doctypes",
			callback: function(r) {
				frm.set_df_property("select_doctype", "options", r.message);
			}
		});
	},
	refresh: function(frm) {
		frm.disable_save();

		frm.get_field("file_to_rename").df.options = {
			restrictions: {
				allowed_file_types: [".csv"],
			},
		};
		if (!frm.doc.file_to_rename) {
			frm.get_field("rename_log").$wrapper.html("");
		}
		frm.page.set_primary_action(__("Rename"), function() {
			frm.get_field("rename_log").$wrapper.html("<p>Renaming...</p>");
			frappe.call({
				method: "erpnext.utilities.doctype.rename_tool.rename_tool.upload",
				args: {
					select_doctype: frm.doc.select_doctype
				},
				callback: function(r) {
					frm.get_field("rename_log").$wrapper.html(r.message.join("<br>"));
				}
			});
		});
	}
})
