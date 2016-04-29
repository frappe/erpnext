// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Time Log", {
	onload: function(frm) {
		if (frm.doc.__islocal) {
			if (frm.doc.for_manufacturing) {
				frappe.ui.form.trigger("Time Log", "production_order");
			}
			if (frm.doc.from_time && frm.doc.to_time) {
				frappe.ui.form.trigger("Time Log", "to_time");
			}
		}
		frm.set_query('task', function() {
			return {
				filters:{
					'project': frm.doc.project
				}
			}
		});
	},
	refresh: function(frm) {
		// set default user if created
		if (frm.doc.__islocal && !frm.doc.user) {
			frm.set_value("user", user);
		}
		if (frm.doc.status==='In Progress' && !frm.is_new()) {
			frm.add_custom_button(__('Finish'), function() {
				frappe.prompt({
					fieldtype: 'Datetime',
					fieldname: 'to_time',
					label: __('End Time'),
					'default': dateutil.now_datetime()
					}, function(value) {
						frm.set_value('to_time', value.to_time);
						frm.save();
					});
			}).addClass('btn-primary');
		}


		frm.toggle_reqd("activity_type", !frm.doc.for_manufacturing);
	},
	hours: function(frm) {
		if(!frm.doc.from_time) {
			frm.set_value("from_time", frappe.datetime.now_datetime());
		}
		var d = moment(frm.doc.from_time);
		d.add(frm.doc.hours, "hours");
		frm._setting_hours = true;
		frm.set_value("to_time", d.format(moment.defaultDatetimeFormat));
		frm._setting_hours = false;

		frm.trigger('calculate_cost');
	},
	before_save: function(frm) {
		frm.doc.production_order && frappe.model.remove_from_locals("Production Order",
			frm.doc.production_order);
	},
	to_time: function(frm) {
		if(frm._setting_hours) return;
		frm.set_value("hours", moment(cur_frm.doc.to_time).diff(moment(cur_frm.doc.from_time),
			"seconds") / 3600);
	},
	calculate_cost: function(frm) {
		frm.set_value("costing_amount", frm.doc.costing_rate * frm.doc.hours);
		if (frm.doc.billable==1){
			frm.set_value("billing_amount", (frm.doc.billing_rate * frm.doc.hours) + frm.doc.additional_cost);
		}
	},
	additional_cost: function(frm) {
		frm.trigger('calculate_cost');
	},
	activity_type: function(frm) {
		if (frm.doc.activity_type){
			return frappe.call({
				method: "erpnext.projects.doctype.time_log.time_log.get_activity_cost",
				args: {
					"employee": frm.doc.employee,
					"activity_type": frm.doc.activity_type
				},
				callback: function(r) {
					if(!r.exc && r.message) {
						frm.set_value("costing_rate", r.message.costing_rate);
						frm.set_value("billing_rate", r.message.billing_rate);
						frm.trigger('calculate_cost');
					}
				}
			});
		}
	},
	employee: function(frm) {
		frm.trigger('activity_type');
	},
	billable: function(frm) {
		if (frm.doc.billable==1) {
			frm.trigger('calculate_cost');
		}
		else {
			frm.set_value("billing_amount", 0);
			frm.set_value("additional_cost", 0);
		}
	}

});
