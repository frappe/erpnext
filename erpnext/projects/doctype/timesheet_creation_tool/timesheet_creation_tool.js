// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Timesheet Creation Tool', {
	onload: function(frm) {
		frm.set_value("company", '');
		frm.set_value("employees", []);
		frm.set_value("time_logs", []);
	},

	refresh: function(frm) {
		frm.disable_save();
	},

	create_timesheet: function(frm) {
		frappe.call({
			doc: frm.doc,
			freeze: true,
			method: "create_timesheet",
			freeze_message: __("Creating Timesheet"),
			callback: (r) => {
				console.log(r);
				if(!r.exc){
					frappe.msgprint(__("Timesheet created"));
					frm.clear_table("employees");
					frm.clear_table("time_logs");
					frm.refresh_fields();
					frm.reload_doc();
				}
			}
		});
	},

	submit_timesheet: function(frm) {

	}

});