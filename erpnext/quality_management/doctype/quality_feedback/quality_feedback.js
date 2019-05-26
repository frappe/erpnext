// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Feedback', {
	refresh: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
	},
	template: function(frm){
		frm.call("get_quality_feedback_template", {
			"template": frm.doc.template
		}, () => {
			frm.refresh();
		});
	}
});
