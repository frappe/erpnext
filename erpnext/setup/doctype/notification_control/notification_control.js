// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Notification Control", {
	refresh: function(frm) {
		frm.page.set_primary_action(__('Update'), function() { frm.events.set_message(frm); });
	},
	select_transaction: function(frm) {
		frm.set_value("custom_message", frm.doc[frm.events.get_fieldname(frm)]);
	},
	set_message: function(frm) {
		if(frm.doc.select_transaction && frm.doc.select_transaction !== "") {
			frm.set_value(frm.events.get_fieldname(frm), frm.doc.custom_message);
		}
		frm.save();
	},
	get_fieldname: function(frm) {
		return frm.doc.select_transaction.replace(" ", "_").toLowerCase() + "_message";
	},
	after_save: function(frm) {
		// update notification settings in current session
		frappe.boot.notification_settings = frm.doc;
	}
});
