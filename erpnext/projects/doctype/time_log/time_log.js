// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Time Log", "onload", function(frm) {
	frm.set_query("task", erpnext.queries.task);
	if (frm.doc.time_log_for == "Manufacturing") {
		frappe.ui.form.trigger("Time Log", "production_order");
	}
});

frappe.ui.form.on("Time Log", "refresh", function(frm) {
	var is_manufacturing = frm.doc.time_log_for=="Manufacturing" ? true : false;
	frm.toggle_reqd("production_order", is_manufacturing);
	frm.toggle_reqd("operation", is_manufacturing);
	frm.toggle_reqd("completed_qty", is_manufacturing);
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

// set hours if to_time is updated
frappe.ui.form.on("Time Log", "to_time", function(frm) {
	if(frm._setting_hours) return;
	frm.set_value("hours", moment(cur_frm.doc.to_time).diff(moment(cur_frm.doc.from_time),
		"hours"));
});

cur_frm.set_query("production_order", function(doc) {
	return {
		"filters": {
			"docstatus": 1
		}
	};
});

cur_frm.add_fetch('task','project','project');

$.extend(cur_frm.cscript, {
	production_order: function(doc) {
		if (doc.production_order){
			var operations = [];
			frappe.model.with_doc("Production Order", doc.production_order, function(pro) {
				doc = frappe.get_doc("Production Order",pro);
				$.each(doc.production_order_operations , function(i, row){
					operations[i] = (i+1) +". "+ row.operation;
				});
			frappe.meta.get_docfield("Time Log", "operation", me.frm.doc.name).options = "\n" + operations.join("\n");
			refresh_field("operation");
			})
		}
	},

	operation: function(doc) {
		return frappe.call({
			method: "erpnext.projects.doctype.time_log.time_log.get_workstation",
			args: {
				"production_order": doc.production_order,
				"operation": doc.operation
			},
			callback: function(r) {
				if(!r.exc) {
					console.log(r.message)
					cur_frm.set_value("workstation", r.message)
				}
			}
		});
	}
});
