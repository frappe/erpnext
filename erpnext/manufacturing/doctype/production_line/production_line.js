// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Line", {
	before_save(frm) {
        if (frm.is_new() && frm.doc.line_code) {
            frm.doc.__unsaved = 1;
            frm.set_value("__newname", frm.doc.line_code);
        }
    },

    refresh(frm) {

	},
});
