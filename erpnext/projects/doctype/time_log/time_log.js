// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Time Log", "onload", function(frm) {
	frm.set_query("task", erpnext.queries.task);
	if (frm.doc.for_manufacturing) {
		frappe.ui.form.trigger("Time Log", "production_order");
	}
});

frappe.ui.form.on("Time Log", "refresh", function(frm) {
	// set default user if created
	if (frm.doc.__islocal && !frm.doc.user) {
		frm.set_value("user", user);
	}
});


// set to time if hours is updated
frappe.ui.form.on("Time Log", "hours", function(frm) {
	if(!frm.doc.from_time) {
		frm.set_value("from_time", frappe.datetime.now_datetime());
	}
	var d = moment(frm.doc.from_time);
	d.add(frm.doc.hours, "hours");
	frm._setting_hours = true;
	frm.set_value("to_time", d.format(moment.defaultDatetimeFormat));
	frm._setting_hours = false;
});

// clear production order if making time log
frappe.ui.form.on("Time Log", "before_save", function(frm) {
	frm.doc.production_order && frappe.model.remove_from_locals("Production Order",
		frm.doc.production_order);
});

// set hours if to_time is updated
frappe.ui.form.on("Time Log", "to_time", function(frm) {
	if(frm._setting_hours) return;
	frm.set_value("hours", moment(cur_frm.doc.to_time).diff(moment(cur_frm.doc.from_time),
		"hours"));
});