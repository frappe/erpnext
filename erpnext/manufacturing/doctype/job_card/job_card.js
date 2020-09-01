// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Card', {
	setup: function(frm) {
		frm.set_query('operation', function() {
			return {
				query: 'erpnext.manufacturing.doctype.job_card.job_card.get_operations',
				filters: {
					'work_order': frm.doc.work_order
				}
			};
		});
	},

	refresh: function(frm) {

		if(frm.doc.docstatus == 0) {
			frm.set_df_property("operation", "read_only", frm.doc.operation_id ? 1 : 0);
		}
		frappe.flags.pause_job = 0;
		frappe.flags.resume_job = 0;

		if(!frm.doc.__islocal && frm.doc.items && frm.doc.items.length) {
			if (frm.doc.for_quantity != frm.doc.transferred_qty) {
				frm.add_custom_button(__("Material Request"), () => {
					frm.trigger("make_material_request");
				});
			}

			if (frm.doc.for_quantity != frm.doc.transferred_qty) {
				frm.add_custom_button(__("Material Transfer"), () => {
					frm.trigger("make_stock_entry");
				}).addClass("btn-primary");
			}
		}

		frm.trigger("toggle_operation_number");

		if (frm.doc.docstatus == 0 && (frm.doc.for_quantity > frm.doc.total_completed_qty || !frm.doc.for_quantity)
			&& (frm.doc.items || !frm.doc.items.length || frm.doc.for_quantity == frm.doc.transferred_qty)) {
			frm.trigger("prepare_timer_buttons");
		}
	},

	operation: function(frm) {
		frm.trigger("toggle_operation_number");

		if (frm.doc.operation && frm.doc.work_order) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.job_card.job_card.get_operation_details",
				args: {
					"work_order":frm.doc.work_order,
					"operation":frm.doc.operation
				},
				callback: function (r) {
					if (r.message) {
						if (r.message.length == 1) {
							frm.set_value("operation_id", r.message[0].name);
						} else {
							let args = [];

							r.message.forEach((row) => {
								args.push({ "label": row.idx, "value": row.name });
							});

							let description = __("Operation {0} added multiple times in the work order {1}",
								[frm.doc.operation, frm.doc.work_order]);

							frm.set_df_property("operation_row_number", "options", args);
							frm.set_df_property("operation_row_number", "description", description);
						}

						frm.trigger("toggle_operation_number");
					}
				}
			})
		}
	},

	operation_row_number(frm) {
		if (frm.doc.operation_row_number) {
			frm.set_value("operation_id", frm.doc.operation_row_number);
		}
	},

	toggle_operation_number(frm) {
		frm.toggle_display("operation_row_number", !frm.doc.operation_id && frm.doc.operation);
		frm.toggle_reqd("operation_row_number", !frm.doc.operation_id && frm.doc.operation);
	},

	prepare_timer_buttons: function(frm) {
		frm.trigger("make_dashboard");
		if (!frm.doc.job_started) {
			frm.add_custom_button(__("Start"), () => {
				if (!frm.doc.employee) {
					frappe.prompt({fieldtype: 'Link', label: __('Employee'), options: "Employee",
						fieldname: 'employee'}, d => {
						if (d.employee) {
							frm.set_value("employee", d.employee);
						} else {
							frm.events.start_job(frm);
						}
					}, __("Enter Value"), __("Start"));
				} else {
					frm.events.start_job(frm);
				}
			}).addClass("btn-primary");
		} else if (frm.doc.status == "On Hold") {
			frm.add_custom_button(__("Resume"), () => {
				frappe.flags.resume_job = 1;
				frm.events.start_job(frm);
			}).addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Pause"), () => {
				frappe.flags.pause_job = 1;
				frm.set_value("status", "On Hold");
				frm.events.complete_job(frm);
			});

			frm.add_custom_button(__("Complete"), () => {
				let completed_time = frappe.datetime.now_datetime();
				frm.trigger("hide_timer");

				if (frm.doc.for_quantity) {
					frappe.prompt({fieldtype: 'Float', label: __('Completed Quantity'),
						fieldname: 'qty', reqd: 1, default: frm.doc.for_quantity}, data => {
							frm.events.complete_job(frm, completed_time, data.qty);
						}, __("Enter Value"), __("Complete"));
				} else {
					frm.events.complete_job(frm, completed_time, 0);
				}
			}).addClass("btn-primary");
		}
	},

	start_job: function(frm) {
		let row = frappe.model.add_child(frm.doc, 'Job Card Time Log', 'time_logs');
		row.from_time = frappe.datetime.now_datetime();
		frm.set_value('job_started', 1);
		frm.set_value('started_time' , row.from_time);
		frm.set_value("status", "Work In Progress");

		if (!frappe.flags.resume_job) {
			frm.set_value('current_time' , 0);
		}

		frm.save();
	},

	complete_job: function(frm, completed_time, completed_qty) {
		frm.doc.time_logs.forEach(d => {
			if (d.from_time && !d.to_time) {
				d.to_time = completed_time || frappe.datetime.now_datetime();
				d.completed_qty = completed_qty || 0;

				if(frappe.flags.pause_job) {
					let currentIncrement = moment(d.to_time).diff(moment(d.from_time),"seconds") || 0;
					frm.set_value('current_time' , currentIncrement + (frm.doc.current_time || 0));
				} else {
					frm.set_value('started_time' , '');
					frm.set_value('job_started', 0);
					frm.set_value('current_time' , 0);
				}

				frm.save();
			}
		});
	},

	validate: function(frm) {
		if ((!frm.doc.time_logs || !frm.doc.time_logs.length) && frm.doc.started_time) {
			frm.trigger("reset_timer");
		}
	},

	employee: function(frm) {
		if (frm.doc.job_started && !frm.doc.current_time) {
			frm.trigger("reset_timer");
		} else {
			frm.events.start_job(frm);
		}
	},

	reset_timer: function(frm) {
		frm.set_value('started_time' , '');
		frm.set_value('job_started', 0);
		frm.set_value('current_time' , 0);
	},

	make_dashboard: function(frm) {
		if(frm.doc.__islocal)
			return;

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold;margin:0px 13px 0px 2px;
				color:#545454;font-size:18px;display:inline-block;vertical-align:text-bottom;>
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.toolbar.page.add_inner_message(timer);

		let currentIncrement = frm.doc.current_time || 0;
		if (frm.doc.started_time || frm.doc.current_time) {
			if (frm.doc.status == "On Hold") {
				updateStopwatch(currentIncrement);
			} else {
				currentIncrement += moment(frappe.datetime.now_datetime()).diff(moment(frm.doc.started_time),"seconds");
				initialiseTimer();
			}

			function initialiseTimer() {
				const interval = setInterval(function() {
					var current = setCurrentIncrement();
					updateStopwatch(current);
				}, 1000);
			}

			function updateStopwatch(increment) {
				var hours = Math.floor(increment / 3600);
				var minutes = Math.floor((increment - (hours * 3600)) / 60);
				var seconds = increment - (hours * 3600) - (minutes * 60);

				$(section).find(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
				$(section).find(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
				$(section).find(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
			}

			function setCurrentIncrement() {
				currentIncrement += 1;
				return currentIncrement;
			}
		}
	},

	hide_timer: function(frm) {
		frm.toolbar.page.inner_toolbar.find(".stopwatch").remove();
	},

	for_quantity: function(frm) {
		frm.doc.items = [];
		frm.call({
			method: "get_required_items",
			doc: frm.doc,
			callback: function() {
				refresh_field("items");
			}
		})
	},

	make_material_request: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_material_request",
			frm: frm,
			run_link_triggers: true
		});
	},

	make_stock_entry: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
			frm: frm,
			run_link_triggers: true
		});
	},

	timer: function(frm) {
		return `<button> Start </button>`
	},

	set_total_completed_qty: function(frm) {
		frm.doc.total_completed_qty = 0;
		frm.doc.time_logs.forEach(d => {
			if (d.completed_qty) {
				frm.doc.total_completed_qty += d.completed_qty;
			}
		});

		refresh_field("total_completed_qty");
	}
});

frappe.ui.form.on('Job Card Time Log', {
	completed_qty: function(frm) {
		frm.events.set_total_completed_qty(frm);
	},

	to_time: function(frm) {
		frm.set_value('job_started', 0);
		frm.set_value('started_time', '');
	}
})