// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/projects/timesheet_common.js' %};

frappe.ui.form.on('Timesheet Creation Tool', {
	onload: function(frm) {
		frm.set_value("company", '');
		frm.set_value("employees", []);
		frm.set_value("time_logs", []);
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__("Make Timesheets"), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				freeze: true,
				btn: $(btn_primary),
				method: "make_timesheet",
				freeze_message: __("Creating Timesheets"),
				callback: (r) => {
					if(!r.exc){
						frappe.msgprint(__("Timesheets submitted."));
						frm.clear_table("employees");
						frm.clear_table("time_logs");
						frm.refresh_fields();
						frm.reload_doc();
					}
				}
			});
		});
	}
});
