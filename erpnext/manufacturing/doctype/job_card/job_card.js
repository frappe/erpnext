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

		frm.set_query("item_code", "scrap_items", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});

		frm.set_query("operation", "time_logs", () => {
			let operations = (frm.doc.sub_operations || []).map((d) => d.sub_operation);
			return {
				filters: {
					name: ["in", operations],
				},
			};
		});

		frm.events.set_company_filters(frm, "target_warehouse");
		frm.events.set_company_filters(frm, "source_warehouse");
		frm.events.set_company_filters(frm, "wip_warehouse");
		frm.set_query("source_warehouse", "items", () => {
			return {
				filters: {
					company: frm.doc.company,
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

		frm.set_query("employee", () => {
			return {
				filters: {
					company: frm.doc.company,
					status: "Active",
				},
			};
		});
	},

	set_company_filters(frm, fieldname) {
		frm.set_query(fieldname, () => {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
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
			frm.doc.track_semi_finished_goods &&
			frm.doc.docstatus === 1 &&
			!frm.doc.is_subcontracted &&
			(frm.doc.skip_material_transfer || frm.doc.transferred_qty > 0) &&
			flt(frm.doc.for_quantity) + flt(frm.doc.process_loss_qty) > flt(frm.doc.manufactured_qty)
		) {
			frm.add_custom_button(__("Make Stock Entry"), () => {
				frappe.confirm(
					__("Do you want to submit the stock entry?"),
					() => {
						frm.events.make_manufacture_stock_entry(frm, 1);
					},
					() => {
						frm.events.make_manufacture_stock_entry(frm, 0);
					}
				);
			}).addClass("btn-primary");
		}
	},

	make_manufacture_stock_entry(frm, submit_entry) {
		frm.call({
			method: "make_stock_entry_for_semi_fg_item",
			args: {
				auto_submit: submit_entry,
			},
			doc: frm.doc,
			freeze: true,
			callback() {
				frm.reload_doc();
			},
		});
	},

	refresh: function (frm) {
		frm.trigger("setup_stock_entry");

		let has_items = frm.doc.items && frm.doc.items.length;
		frm.trigger("make_fields_read_only");

		if (!frm.is_new() && frm.doc.__onload?.work_order_closed) {
			frm.disable_save();
			return;
		}

		if (frm.doc.is_subcontracted) {
			frm.trigger("make_subcontracting_po");
			return;
		}

		let has_stock_entry = frm.doc.__onload && frm.doc.__onload.has_stock_entry ? true : false;

		frm.toggle_enable("for_quantity", !has_stock_entry);

		if (frm.doc.docstatus != 0) {
			frm.fields_dict["time_logs"].grid.update_docfield_property("completed_qty", "read_only", 1);
			frm.fields_dict["time_logs"].grid.update_docfield_property("time_in_mins", "read_only", 1);
		}

		if (!frm.is_new() && !frm.doc.skip_material_transfer && frm.doc.docstatus < 2) {
			let to_request = frm.doc.for_quantity > frm.doc.transferred_qty;
			let excess_transfer_allowed = frm.doc.__onload.job_card_excess_transfer;

			if (has_items && (to_request || excess_transfer_allowed)) {
				frm.add_custom_button(
					__("Material Request"),
					() => {
						frm.trigger("make_material_request");
					},
					__("Create")
				);
			}

			// check if any row has untransferred materials
			// in case of multiple items in JC
			let to_transfer = frm.doc.items.some((row) => row.transferred_qty < row.required_qty);

			if (has_items && (to_transfer || excess_transfer_allowed)) {
				frm.add_custom_button(
					__("Material Transfer"),
					() => {
						frm.trigger("make_stock_entry");
					},
					__("Create")
				);
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
				!frm.doc.finished_good ||
				!has_items?.length)
		) {
			let last_row = {};
			if (frm.doc.sub_operations?.length && frm.doc.time_logs?.length) {
				last_row = get_last_row(frm.doc.time_logs);
			}

			if (
				(!frm.doc.time_logs?.length || (frm.doc.sub_operations?.length && last_row?.to_time)) &&
				!frm.doc.is_paused
			) {
				frm.add_custom_button(__("Start Job"), () => {
					let from_time = frappe.datetime.now_datetime();
					if ((frm.doc.employee && !frm.doc.employee.length) || !frm.doc.employee) {
						frappe.prompt(
							{
								fieldtype: "Table MultiSelect",
								label: __("Select Employees"),
								options: "Job Card Time Log",
								fieldname: "employees",
								filters: {
									status: "Active",
								},
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
				let manufactured_qty = frm.doc.manufactured_qty || frm.doc.total_completed_qty;
				if (frm.doc.for_quantity - (manufactured_qty + frm.doc.process_loss_qty) > 0) {
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

	complete_job_card(frm) {
		let fields = [
			{
				fieldtype: "Float",
				label: __("Qty to Manufacture"),
				fieldname: "for_quantity",
				reqd: 1,
				default: frm.doc.for_quantity,
				change() {
					let doc = frm.job_completion_dialog;

					doc.set_value("completed_qty", doc.get_value("for_quantity"));
					doc.set_value("process_loss_qty", 0);
				},
			},
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "completed_qty",
				reqd: 1,
				default: frm.doc.for_quantity - frm.doc.total_completed_qty,
				change() {
					let doc = frm.job_completion_dialog;

					let process_loss_qty = doc.get_value("for_quantity") - doc.get_value("completed_qty");
					if (process_loss_qty > 0 && process_loss_qty != doc.get_value("process_loss_qty")) {
						doc.set_value("process_loss_qty", process_loss_qty);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Process Loss Quantity"),
				fieldname: "process_loss_qty",
				onchange() {
					let doc = frm.job_completion_dialog;

					let completed_qty = doc.get_value("for_quantity") - doc.get_value("process_loss_qty");
					doc.set_value("completed_qty", completed_qty);
				},
			},
			{
				fieldtype: "Section Break",
			},
		];

		if (frm.doc.sub_operations?.length) {
			fields.push({
				fieldtype: "Link",
				label: __("Sub Operation"),
				fieldname: "sub_operation",
				options: "Operation",
				get_query() {
					let non_completed_operations = frm.doc.sub_operations.filter(
						(d) => d.status === "Pending"
					);
					return {
						filters: {
							name: ["in", non_completed_operations.map((d) => d.sub_operation)],
						},
					};
				},
				reqd: 1,
			});
		}

		let last_completed_row = get_last_completed_row(frm.doc.time_logs);
		let last_row = {};
		if (frm.doc.sub_operations?.length && frm.doc.time_logs?.length) {
			last_row = get_last_row(frm.doc.time_logs);
		}

		if (!last_completed_row || !last_completed_row.to_time || !last_row.to_time) {
			fields.push({
				fieldtype: "Datetime",
				label: __("End Time"),
				fieldname: "end_time",
				default: frappe.datetime.now_datetime(),
			});
		}

		frm.job_completion_dialog = frappe.prompt(
			fields,
			(data) => {
				if (data.qty <= 0) {
					frappe.throw(__("Quantity should be greater than 0"));
				}

				frm.call({
					method: "complete_job_card",
					doc: frm.doc,
					args: {
						qty: data.completed_qty,
						for_quantity: data.for_quantity,
						end_time: data.end_time,
						sub_operation: data.sub_operation,
					},
					callback: function (r) {
						frm.reload_doc();
					},
				});
			},
			__("Enter Value"),
			__("Update"),
			__("Set Finished Good Quantity")
		);
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
		var section = "";

		function setCurrentIncrement() {
			currentIncrement += 1;
			return currentIncrement;
		}

		function updateStopwatch(increment) {
			var hours = Math.floor(increment / 3600);
			var minutes = Math.floor((increment - hours * 3600) / 60);
			var seconds = Math.floor(flt(increment - hours * 3600 - minutes * 60, 2));

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

		if (frappe.utils.is_xs()) {
			frm.dashboard.add_comment(timer, "white", true);
			section = frm.layout.wrapper.find(".form-message-container");
		} else {
			section = frm.toolbar.page.add_inner_message(timer);
		}

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
	completed_qty: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.completed_qty) {
			frappe.model.set_value(row.doctype, row.name, {
				time_in_mins: 0,
				to_time: "",
			});
		}

		frm.events.set_total_completed_qty(frm);
	},

	to_time: function (frm) {
		frm.set_value("started_time", "");
	},

	time_in_mins(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.time_in_mins) {
			d.to_time = add_mins_to_time(d.from_time, d.time_in_mins);
			frappe.model.set_value(cdt, cdn, "to_time", d.to_time);
		}
	},
});

function get_seconds_diff(d1, d2) {
	return moment(d1).diff(d2, "seconds");
}

function add_mins_to_time(datetime, mins) {
	let new_date = moment(datetime).add(mins, "minutes");

	return new_date.format("YYYY-MM-DD HH:mm:ss");
}

function get_last_completed_row(time_logs) {
	let completed_rows = time_logs.filter((d) => d.to_time);

	if (completed_rows?.length) {
		let last_completed_row = completed_rows[completed_rows.length - 1];
		return last_completed_row;
	}
}

function get_last_row(time_logs) {
	return time_logs[time_logs.length - 1] || {};
}
