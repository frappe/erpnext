// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Review', {
	onload: function(frm){
		frm.set_value("date", frappe.datetime.get_today());
	},
	goal: function(frm) {
		frm.call("get_quality_goal", {
			"goal": frm.doc.goal,
		}, () => {
			frm.refresh();
		});
	},
});