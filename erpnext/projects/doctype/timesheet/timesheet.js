// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Timesheet", {
	setup: function(frm) {
		frm.add_fetch('employee', 'employee_name', 'employee_name');
		frm.fields_dict.employee.get_query = function() {
			return {
				filters:{
					'status': 'Active'
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('task').get_query = function(frm, cdt, cdn) {
			var child = locals[cdt][cdn];
			return{
				filters: {
					'project': child.project,
					'status': ["!=", "Closed"]
				}
			}
		}

		frm.fields_dict['time_logs'].grid.get_field('project').get_query = function() {
			return{
				filters: {
					'company': frm.doc.company
				}
			}
		}
	},

	onload: function(frm){
		if (frm.doc.__islocal && frm.doc.time_logs) {
			calculate_time_and_amount(frm);
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			if(frm.doc.per_billed < 100 && frm.doc.total_billable_hours && frm.doc.total_billable_hours > frm.doc.total_billed_hours){
				frm.add_custom_button(__("Make Sales Invoice"), function() { frm.trigger("make_invoice") },
					"fa fa-file-alt");
			}

			if(!frm.doc.salary_slip && frm.doc.employee){
				frm.add_custom_button(__("Make Salary Slip"), function() { frm.trigger("make_salary_slip") },
					"fa fa-file-alt");
			}
		}

		if (frm.doc.total_hours && frm.doc.docstatus < 2) {
			frm.add_custom_button(__('Start Timer'), function() {
				frm.trigger("timer")
			}).addClass("btn-primary");
		}

		if(frm.doc.per_billed > 0) {
			frm.fields_dict["time_logs"].grid.toggle_enable("billing_hours", false);
			frm.fields_dict["time_logs"].grid.toggle_enable("billable", false);
		}
	},

	timer: function(frm) {
		let dialog = new frappe.ui.Dialog({
			title: __("Timer"),
			fields: [
				{"fieldtype": "Select", "label": __("Activity"),
					"fieldname": "activity",
					"options": frm.doc.time_logs.map(d => d.activity_type),
					"reqd": 1 },
				{"fieldtype": "Select", "label": __("Project"),
					"fieldname": "project",
					"options": frm.doc.time_logs.map(d => d.project)},
				{"fieldtype": "Select", "label": __("Hours"),
					"fieldname": "hours",
					"options": frm.doc.time_logs.map(d => d.hours)}
			]
		});
		dialog.wrapper.append(frappe.render_template("timesheet"));
		frm.trigger("control_timer");
		dialog.show();
	},

	control_timer: function() {
		var interval = null;
		var currentIncrement = 0;
		var isPaused = false;
		var initialised = false;
		var clicked = false;
		var paused_time = 0;

		$(".playpause").click(function(e) {
			if (!cur_dialog.get_value('activity')) {
				frappe.msgprint(__("Please select Activity"));
				return false;
			}
			if (clicked) {
				e.preventDefault();
				return false;
			}

			if (!initialised) {
				initialised = true;
				isPaused = false;
				$(".playpause span").removeClass();
				$(".playpause span").addClass("pause");
				initialiseTimer();
			}
			else {
				$(".playpause span").removeClass();
				if (isPaused) {
					isPaused = false;
					$(".playpause span").addClass("pause");
				}
				else {
					isPaused = true;
					$(".playpause span").addClass("play");
					paused_time = currentIncrement;
				}
			}
		});

		$(".stop").click(function() {
			console.log(currentIncrement);
			reset();
		});

		function initialiseTimer() {
			interval = setInterval(function() {
				if (isPaused) return;
				var current = setCurrentIncrement();
				updateStopwatch(current);
			}, 1000);
		}

		function updateStopwatch(increment) {
			var hours = Math.floor(increment / 3600);
			var minutes = Math.floor((increment - (hours * 3600)) / 60);
			var seconds = increment - (hours * 3600) - (minutes * 60);
			// if(!$('modal-open:visible')){
			// 	reset();
			// }
			if (!$('.modal-dialog').is(':visible')) {
				reset();
			}
			if(hours > 99)
			reset();
			if(cur_dialog && cur_dialog.get_value('hours') == hours) {
				isPaused = true;
				initialised = false;
				frappe.utils.play_sound("alert");
				frappe.msgprint(__("Timer exceeded the given hours"));
			}
			$(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
			$(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
			$(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
		}

		function setCurrentIncrement() {
			currentIncrement += 1;
			return currentIncrement;
		}

		function reset() {
			currentIncrement = 0;
			isPaused = true;
			initialised = false;
			clearInterval(interval);
			$(".hours").text("00");
			$(".minutes").text("00");
			$(".seconds").text("00");
			$(".playpause span").removeClass();
			$(".playpause span").addClass("play");
		}
	},

	make_invoice: function(frm) {
		let dialog = new frappe.ui.Dialog({
			title: __("Select Item (optional)"),
			fields: [
				{"fieldtype": "Link", "label": __("Item Code"), "fieldname": "item_code", "options":"Item"},
				{"fieldtype": "Link", "label": __("Customer"), "fieldname": "customer", "options":"Customer"}
			]
		});

		dialog.set_primary_action(__("Make Sales Invoice"), () => {
			var args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.projects.doctype.timesheet.timesheet.make_sales_invoice",
				args: {
					"source_name": frm.doc.name,
					"item_code": args.item_code,
					"customer": args.customer
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			})
		})

		dialog.show();
	},

	make_salary_slip: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.timesheet.timesheet.make_salary_slip",
			frm: frm
		});
	},
})

frappe.ui.form.on("Timesheet Detail", {
	time_logs_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn);
	},

	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(frm._setting_hours) return;
		frappe.model.set_value(cdt, cdn, "hours", moment(child.to_time).diff(moment(child.from_time),
			"seconds") / 3600);
	},

	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	billing_hours: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	costing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billable: function(frm, cdt, cdn) {
		update_billing_hours(frm, cdt, cdn);
		update_time_rates(frm, cdt, cdn);
		calculate_billing_costing_amount(frm, cdt, cdn);
	},

	activity_type: function(frm, cdt, cdn) {
		frm.script_manager.copy_from_first_row('time_logs', frm.selected_doc,
			'project');

		frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
			args: {
				employee: frm.doc.employee,
				activity_type: frm.selected_doc.activity_type
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'billing_rate', r.message['billing_rate']);
					frappe.model.set_value(cdt, cdn, 'costing_rate', r.message['costing_rate']);
					calculate_billing_costing_amount(frm, cdt, cdn);
				}
			}
		})
	}
});

var calculate_end_time = function(frm, cdt, cdn) {
	let child = locals[cdt][cdn];

	if(!child.from_time) {
		// if from_time value is not available then set the current datetime
		frappe.model.set_value(cdt, cdn, "from_time", frappe.datetime.get_datetime_as_string());
	}

	let d = moment(child.from_time);
	if(child.hours) {
		d.add(child.hours, "hours");
		frm._setting_hours = true;
		frappe.model.set_value(cdt, cdn, "to_time",
			d.format(moment.defaultDatetimeFormat)).then(() => {
				frm._setting_hours = false;
			});
	}


	if((frm.doc.__islocal || frm.doc.__onload.maintain_bill_work_hours_same) && child.hours){
		frappe.model.set_value(cdt, cdn, "billing_hours", child.hours);
	}
}

var update_billing_hours = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];
	if(!child.billable) frappe.model.set_value(cdt, cdn, 'billing_hours', 0.0);
}

var update_time_rates = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];
	if(!child.billable){
		frappe.model.set_value(cdt, cdn, 'billing_rate', 0.0);
	}
}

var calculate_billing_costing_amount = function(frm, cdt, cdn){
	var child = locals[cdt][cdn];
	var billing_amount = 0.0;
	var costing_amount = 0.0;

	if(child.billing_hours && child.billable){
		billing_amount = (child.billing_hours * child.billing_rate);
	}
	costing_amount = flt(child.costing_rate * child.hours);
	frappe.model.set_value(cdt, cdn, 'billing_amount', billing_amount);
	frappe.model.set_value(cdt, cdn, 'costing_amount', costing_amount);
	calculate_time_and_amount(frm);
}

var calculate_time_and_amount = function(frm) {
	var tl = frm.doc.time_logs || [];
	var total_working_hr = 0;
	var total_billing_hr = 0;
	var total_billable_amount = 0;
	var total_costing_amount = 0;
	for(var i=0; i<tl.length; i++) {
		if (tl[i].hours) {
			total_working_hr += tl[i].hours;
			total_billable_amount += tl[i].billing_amount;
			total_costing_amount += tl[i].costing_amount;

			if(tl[i].billable){
				total_billing_hr += tl[i].billing_hours;
			}
		}
	}

	frm.set_value("total_billable_hours", total_billing_hr);
	frm.set_value("total_hours", total_working_hr);
	frm.set_value("total_billable_amount", total_billable_amount);
	frm.set_value("total_costing_amount", total_costing_amount);
}