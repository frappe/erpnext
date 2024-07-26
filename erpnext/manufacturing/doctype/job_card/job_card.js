// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Card", {
	setup: function (frm) {
		frm.set_query("operation", function () {
			return {
				query: "erpnext.manufacturing.doctype.job_card.job_card.get_operations",
				filters: {
					work_order: frm.doc.work_order,
				},
			};
		});

		frm.set_query("serial_and_batch_bundle", () => {
			return {
				filters: {
					item_code: frm.doc.production_item,
					voucher_type: frm.doc.doctype,
					voucher_no: ["in", [frm.doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});

		frm.set_indicator_formatter("sub_operation", function (doc) {
			if (doc.status == "Pending") {
				return "red";
			} else {
				return doc.status === "Complete" ? "green" : "orange";
			}
		});
	},

	make_fields_read_only(frm) {
		if (frm.doc.docstatus === 1) {
			frm.set_df_property("employee", "read_only", 1);
			frm.set_df_property("time_logs", "read_only", 1);
		}

		if (frm.doc.is_subcontracted) {
			frm.set_df_property("wip_warehouse", "label", __("Supplier Warehouse"));
		}
	},

	setup_stock_entry(frm) {
		if (
			frm.doc.finished_good &&
			frm.doc.docstatus === 1 &&
			!frm.doc.is_subcontracted &&
			flt(frm.doc.for_quantity) + flt(frm.doc.process_loss_qty) > flt(frm.doc.manufactured_qty)
		) {
			frm.add_custom_button(__("Make Stock Entry"), () => {
				frm.call({
					method: "make_stock_entry_for_semi_fg_item",
					args: {
						auto_submit: 1,
					},
					doc: frm.doc,
					freeze: true,
					callback() {
						frm.reload_doc();
					},
				});
			}).addClass("btn-primary");
		}
	},

	refresh: function (frm) {
		frm.trigger("setup_stock_entry");

		let has_items = frm.doc.items && frm.doc.items.length;
		frm.trigger("make_fields_read_only");

		if (!frm.is_new() && frm.doc.__onload.work_order_closed) {
			frm.disable_save();
			return;
		}

		if (frm.doc.is_subcontracted) {
			frm.trigger("make_subcontracting_po");
			return;
		}

		let has_stock_entry = frm.doc.__onload && frm.doc.__onload.has_stock_entry ? true : false;

		frm.toggle_enable("for_quantity", !has_stock_entry);

		if (!frm.is_new() && !frm.doc.skip_material_transfer && has_items && frm.doc.docstatus < 2) {
			let to_request = frm.doc.for_quantity > frm.doc.transferred_qty;
			let excess_transfer_allowed = frm.doc.__onload.job_card_excess_transfer;

			if (to_request || excess_transfer_allowed) {
				frm.add_custom_button(__("Material Request"), () => {
					frm.trigger("make_material_request");
				});
			}

			// check if any row has untransferred materials
			// in case of multiple items in JC
			let to_transfer = frm.doc.items.some((row) => row.transferred_qty < row.required_qty);

			if (to_transfer || excess_transfer_allowed) {
				frm.add_custom_button(__("Material Transfer"), () => {
					frm.trigger("make_stock_entry");
				});
			}
		}

		if (frm.doc.docstatus == 1 && !frm.doc.is_corrective_job_card && !frm.doc.finished_good) {
			frm.trigger("setup_corrective_job_card");
		}

		frm.set_query("quality_inspection", function () {
			return {
				query: "erpnext.stock.doctype.quality_inspection.quality_inspection.quality_inspection_query",
				filters: {
					item_code: frm.doc.production_item,
					reference_name: frm.doc.name,
				},
			};
		});

		frm.trigger("toggle_operation_number");

		if (
			frm.doc.for_quantity + frm.doc.process_loss_qty > frm.doc.total_completed_qty &&
			(frm.doc.skip_material_transfer ||
				frm.doc.transferred_qty >= frm.doc.for_quantity + frm.doc.process_loss_qty ||
				!frm.doc.finished_good)
		) {
			if (!frm.doc.time_logs?.length) {
				frm.add_custom_button(__("Start Job"), () => {
					let from_time = frappe.datetime.now_datetime();
					if ((frm.doc.employee && !frm.doc.employee.length) || !frm.doc.employee) {
						frappe.prompt(
							{
								fieldtype: "Table MultiSelect",
								label: __("Select Employees"),
								options: "Job Card Time Log",
								fieldname: "employees",
							},
							(d) => {
								frm.events.start_timer(frm, from_time, d.employees);
							},
							__("Assign Job to Employee")
						);
					} else {
						frm.events.start_timer(frm, from_time, frm.doc.employee);
					}
				});
			} else if (frm.doc.is_paused) {
				frm.add_custom_button(__("Resume Job"), () => {
					frm.call({
						method: "resume_job",
						doc: frm.doc,
						args: {
							start_time: frappe.datetime.now_datetime(),
						},
						callback() {
							frm.reload_doc();
						},
					});
				});
			} else {
				if (frm.doc.for_quantity - frm.doc.manufactured_qty > 0) {
					if (!frm.doc.is_paused) {
						frm.add_custom_button(__("Pause Job"), () => {
							frm.call({
								method: "pause_job",
								doc: frm.doc,
								args: {
									end_time: frappe.datetime.now_datetime(),
								},
								callback() {
									frm.reload_doc();
								},
							});
						});
					}

					frm.add_custom_button(__("Complete Job"), () => {
						frm.trigger("complete_job_card");
					});
				}

				frm.trigger("make_dashboard");
			}
		}

		frm.trigger("setup_quality_inspection");

		if (frm.doc.work_order) {
			frappe.db.get_value("Work Order", frm.doc.work_order, "transfer_material_against").then((r) => {
				if (r.message.transfer_material_against == "Work Order" && !frm.doc.operation_row_id) {
					frm.set_df_property("items", "hidden", 1);
				}
			});
		}

		let sbb_field = frm.get_docfield("serial_and_batch_bundle");
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = () => {
				return {
					item_code: frm.doc.production_item,
					warehouse: frm.doc.wip_warehouse,
					voucher_type: frm.doc.doctype,
				};
			};
		}
	},

	make_subcontracting_po(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.for_quantity > frm.doc.manufactured_qty) {
			frm.add_custom_button(__("Make Subcontracting PO"), () => {
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.job_card.job_card.make_subcontracting_po",
					frm: frm,
				});
			}).addClass("btn-primary");
		}
	},

	start_timer(frm, start_time, employees) {
		frm.call({
			method: "start_timer",
			doc: frm.doc,
			args: {
				start_time: start_time,
				employees: employees,
			},
			callback: function (r) {
				frm.reload_doc();
				frm.trigger("make_dashboard");
			},
		});
	},

	make_finished_good(frm) {
		let fields = [
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "qty",
				reqd: 1,
				default: frm.doc.for_quantity - frm.doc.manufactured_qty,
			},
			{
				fieldtype: "Datetime",
				label: __("End Time"),
				fieldname: "end_time",
				default: frappe.datetime.now_datetime(),
			},
		];

		frappe.prompt(
			fields,
			(data) => {
				if (data.qty <= 0) {
					frappe.throw(__("Quantity should be greater than 0"));
				}

				frm.call({
					method: "make_finished_good",
					doc: frm.doc,
					args: {
						qty: data.qty,
						end_time: data.end_time,
					},
					callback: function (r) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", doc[0].doctype, doc[0].name);
					},
				});
			},
			__("Enter Value"),
			__("Update"),
			__("Set Finished Good Quantity")
		);
	},

	setup_quality_inspection: function (frm) {
		let quality_inspection_field = frm.get_docfield("quality_inspection");
		quality_inspection_field.get_route_options_for_new_doc = function (frm) {
			return {
				inspection_type: "In Process",
				reference_type: "Job Card",
				reference_name: frm.doc.name,
				item_code: frm.doc.production_item,
				item_name: frm.doc.item_name,
				item_serial_no: frm.doc.serial_no,
				batch_no: frm.doc.batch_no,
				quality_inspection_template: frm.doc.quality_inspection_template,
			};
		};
	},

	setup_corrective_job_card: function (frm) {
		frm.add_custom_button(
			__("Corrective Job Card"),
			() => {
				let operations = frm.doc.sub_operations.map((d) => d.sub_operation).concat(frm.doc.operation);

				let fields = [
					{
						fieldtype: "Link",
						label: __("Corrective Operation"),
						options: "Operation",
						fieldname: "operation",
						get_query() {
							return {
								filters: {
									is_corrective_operation: 1,
								},
							};
						},
					},
					{
						fieldtype: "Link",
						label: __("For Operation"),
						options: "Operation",
						fieldname: "for_operation",
						get_query() {
							return {
								filters: {
									name: ["in", operations],
								},
							};
						},
					},
				];

				frappe.prompt(
					fields,
					(d) => {
						frm.events.make_corrective_job_card(frm, d.operation, d.for_operation);
					},
					__("Select Corrective Operation")
				);
			},
			__("Make")
		);
	},

	make_corrective_job_card: function (frm, operation, for_operation) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_corrective_job_card",
			args: {
				source_name: frm.doc.name,
				operation: operation,
				for_operation: for_operation,
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			},
		});
	},

	operation: function (frm) {
		frm.trigger("toggle_operation_number");

		if (frm.doc.operation && frm.doc.work_order) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.job_card.job_card.get_operation_details",
				args: {
					work_order: frm.doc.work_order,
					operation: frm.doc.operation,
				},
				callback: function (r) {
					if (r.message) {
						if (r.message.length == 1) {
							frm.set_value("operation_id", r.message[0].name);
						} else {
							let args = [];

							r.message.forEach((row) => {
								args.push({ label: row.idx, value: row.name });
							});

							let description = __("Operation {0} added multiple times in the work order {1}", [
								frm.doc.operation,
								frm.doc.work_order,
							]);

							frm.set_df_property("operation_row_number", "options", args);
							frm.set_df_property("operation_row_number", "description", description);
						}

						frm.trigger("toggle_operation_number");
					}
				},
			});
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

	make_time_log: function (frm, args) {
		frm.events.update_sub_operation(frm, args);

		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_time_log",
			args: {
				args: args,
			},
			freeze: true,
			callback: function () {
				frm.reload_doc();
				frm.trigger("make_dashboard");
			},
		});
	},

	update_sub_operation: function (frm, args) {
		if (frm.doc.sub_operations && frm.doc.sub_operations.length) {
			let sub_operations = frm.doc.sub_operations.filter((d) => d.status != "Complete");
			if (sub_operations && sub_operations.length) {
				args["sub_operation"] = sub_operations[0].sub_operation;
			}
		}
	},

	validate: function (frm) {
		if ((!frm.doc.time_logs || !frm.doc.time_logs.length) && frm.doc.started_time) {
			frm.trigger("reset_timer");
		}
	},

	reset_timer: function (frm) {
		frm.set_value("started_time", "");
	},

	make_dashboard: function (frm) {
		if (frm.doc.__islocal) return;

		function setCurrentIncrement() {
			currentIncrement += 1;
			return currentIncrement;
		}

		function updateStopwatch(increment) {
			var hours = Math.floor(increment / 3600);
			var minutes = Math.floor((increment - hours * 3600) / 60);
			var seconds = flt(increment - hours * 3600 - minutes * 60, 2);

			$(section)
				.find(".hours")
				.text(hours < 10 ? "0" + hours.toString() : hours.toString());
			$(section)
				.find(".minutes")
				.text(minutes < 10 ? "0" + minutes.toString() : minutes.toString());
			$(section)
				.find(".seconds")
				.text(seconds < 10 ? "0" + seconds.toString() : seconds.toString());
		}

		function initialiseTimer() {
			const interval = setInterval(function () {
				var current = setCurrentIncrement();
				updateStopwatch(current);
			}, 1000);
		}

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold;margin:0px 13px 0px 2px;
				color:#545454;font-size:18px;display:inline-block;vertical-align:text-bottom;">
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.toolbar.page.add_inner_message(timer);
		let currentIncrement = frm.events.get_current_time(frm);
		if (frm.doc.time_logs?.length && frm.doc.time_logs[cint(frm.doc.time_logs.length) - 1].to_time) {
			updateStopwatch(currentIncrement);
		} else if (frm.doc.status == "On Hold") {
			updateStopwatch(currentIncrement);
		} else {
			initialiseTimer();
		}
	},

	get_current_time(frm) {
		let current_time = 0;

		frm.doc.time_logs.forEach((d) => {
			if (d.to_time) {
				if (d.time_in_mins) {
					current_time += flt(d.time_in_mins, 2) * 60;
				} else {
					current_time += get_seconds_diff(d.to_time, d.from_time);
				}
			} else {
				current_time += get_seconds_diff(frappe.datetime.now_datetime(), d.from_time);
			}
		});

		return current_time;
	},

	hide_timer: function (frm) {
		frm.toolbar.page.inner_toolbar.find(".stopwatch").remove();
	},

	for_quantity: function (frm) {
		frm.doc.items = [];
		frm.call({
			method: "get_required_items",
			doc: frm.doc,
			callback: function () {
				refresh_field("items");
			},
		});
	},

	make_material_request: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_material_request",
			frm: frm,
			run_link_triggers: true,
		});
	},

	make_stock_entry: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
			frm: frm,
			run_link_triggers: true,
		});
	},

	timer: function (frm) {
		return `<button> Start </button>`;
	},

	set_total_completed_qty: function (frm) {
		frm.doc.total_completed_qty = 0;
		frm.doc.time_logs.forEach((d) => {
			if (d.completed_qty) {
				frm.doc.total_completed_qty += d.completed_qty;
			}
		});

		if (frm.doc.total_completed_qty && frm.doc.for_quantity > frm.doc.total_completed_qty) {
			let flt_precision = precision("for_quantity", frm.doc);
			let process_loss_qty =
				flt(frm.doc.for_quantity, flt_precision) - flt(frm.doc.total_completed_qty, flt_precision);

			frm.set_value("process_loss_qty", process_loss_qty);
		}

		refresh_field("total_completed_qty");
	},

	source_warehouse(frm) {
		if (frm.doc.source_warehouse) {
			frm.doc.items.forEach((d) => {
				frappe.model.set_value(d.doctype, d.name, "source_warehouse", frm.doc.source_warehouse);
			});
		}
	},
});

frappe.ui.form.on("Job Card Time Log", {
	completed_qty: function (frm) {
		frm.events.set_total_completed_qty(frm);
	},

	to_time: function (frm) {
		frm.set_value("started_time", "");
	},
});

function get_seconds_diff(d1, d2) {
	return moment(d1).diff(d2, "seconds");
}
