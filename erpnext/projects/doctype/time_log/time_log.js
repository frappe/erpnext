// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Time Log", "onload", function(frm) {
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

var calculate_cost = function(doc) {
	cur_frm.set_value("costing_amount", doc.costing_rate * doc.hours);
	if (doc.billable==1){
		cur_frm.set_value("billing_amount", doc.billing_rate * doc.hours);
	}
}

var get_activity_cost = function(frm) {
	return frappe.call({
		method: "erpnext.projects.doctype.time_log.time_log.get_activity_cost",
		args: {
			"employee": frm.doc.employee,
			"activity_type": frm.doc.activity_type
		},
		callback: function(r) {
			if(!r.exc) {
				cur_frm.set_value("costing_rate", r.message.costing_rate);
				cur_frm.set_value("billing_rate", r.message.billing_rate);
				calculate_cost(frm.doc);
			}
		}
	});
}

frappe.ui.form.on("Time Log", "hours", function(frm) {
	calculate_cost(frm.doc);
});

frappe.ui.form.on("Time Log", "activity_type", function(frm) {
	get_activity_cost(frm);
});

frappe.ui.form.on("Time Log", "employee", function(frm) {
	get_activity_cost(frm);
});

frappe.ui.form.on("Time Log", "billable", function(frm) {
	if (frm.doc.billable==1) {
		calculate_cost(frm.doc);
	}
	else {
		frm.doc("billing_amount", 0);
	}
});

cur_frm.fields_dict['task'].get_query = function(doc) {
	return {
		filters:{
			'project': doc.project
		}
	}	
}
