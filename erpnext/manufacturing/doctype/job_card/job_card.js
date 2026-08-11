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

		frm.set_query("work_order", function () {
			return {
				filters: {
					status: ["not in", ["Cancelled", "Closed", "Stopped"]],
				},
			};
		});
	},

	refresh: function (frm) {
		frappe.flags.pause_job = 0;
		frappe.flags.resume_job = 0;
		let has_items = frm.doc.items && frm.doc.items.length;

		if (!frm.is_new() && frm.doc.__onload?.work_order_closed) {
			frm.disable_save();
			return;
		}

		let has_stock_entry = frm.doc.__onload && frm.doc.__onload.has_stock_entry ? true : false;

		frm.toggle_enable("for_quantity", !has_stock_entry);

		if (!frm.is_new() && has_items && frm.doc.docstatus < 2) {
			const excess_transfer_allowed = frm.doc.__onload.job_card_excess_transfer;
			const to_transfer = frm.doc.items.some((row) => flt(row.transferred_qty) < flt(row.required_qty));
			const to_request = to_transfer;

			if (to_request || excess_transfer_allowed) {
				frm.add_custom_button(
					__("Material Request"),
					() => {
						frm.trigger("make_material_request");
					},
					__("Create")
				);
			}

			if (to_transfer || excess_transfer_allowed) {
				frm.add_custom_button(
					__("Material Transfer"),
					() => {
						frm.trigger("make_stock_entry");
					},
					__("Create")
				);
			}
		}

		if (frm.doc.docstatus == 1 && !frm.doc.is_corrective_job_card) {
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
			frm.doc.docstatus == 0 &&
			!frm.is_new() &&
			(frm.doc.for_quantity > frm.doc.total_completed_qty || !frm.doc.for_quantity) &&
			(!frm.doc.items.length ||
				!frm.doc.items.some((row) => flt(row.transferred_qty) < flt(row.required_qty)))
		) {
			// if Job Card is link to Work Order, the job card must not be able to start if Work Order not "Started"
			// and if stock mvt for WIP is required
			if (frm.doc.work_order) {
				frappe.db.get_value(
					"Work Order",
					frm.doc.work_order,
					["skip_transfer", "status"],
					(result) => {
						if (
							result.skip_transfer === 1 ||
							result.status == "In Process" ||
							frm.doc.transferred_qty > 0 ||
							!frm.doc.items.length
						) {
							frm.trigger("prepare_timer_buttons");
						}
					}
				);
			} else {
				frm.trigger("prepare_timer_buttons");
			}
		}

		frm.trigger("setup_quality_inspection");

		if (frm.doc.work_order) {
			frappe.db.get_value("Work Order", frm.doc.work_order, "transfer_material_against").then((r) => {
				if (r.message.transfer_material_against == "Work Order") {
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

	prepare_timer_buttons: function (frm) {
		frm.trigger("make_dashboard");

<<<<<<< HEAD
		if (!frm.doc.started_time && !frm.doc.current_time) {
			frm.add_custom_button(__("Start Job"), () => {
				if ((frm.doc.employee && !frm.doc.employee.length) || !frm.doc.employee) {
=======
		const { doc } = frm;
		const { time_logs, status } = doc;

		// ── Determine which action buttons to show ────────────────────────
		const has_remaining_qty = doc.for_quantity + doc.process_loss_qty > doc.total_completed_qty;
		const pending_transfer =
			has_items && doc.items.some((row) => flt(row.transferred_qty) < flt(row.required_qty));
		const materials_ready = doc.skip_material_transfer || doc.is_corrective_job_card || !pending_transfer;

		let last_row = {};
		const has_sub_ops_or_pending_qty = doc.sub_operations?.length || doc.pending_qty > 0;
		if (has_sub_ops_or_pending_qty && time_logs?.length) {
			last_row = get_last_row(time_logs);
		}

		const no_time_logs_yet = !time_logs?.length;
		const pending_qty_cycle_done = flt(doc.pending_qty) > 0.0 && last_row?.to_time;
		const sub_operation_cycle_done = doc.sub_operations?.length && last_row?.to_time;
		const should_show_start =
			(no_time_logs_yet || pending_qty_cycle_done || sub_operation_cycle_done) && !doc.is_paused;

		const last_log_complete = time_logs?.length && time_logs[time_logs.length - 1].to_time;
		const is_on_hold = status === "On Hold";
		const is_actively_running = !!(
			time_logs?.length &&
			!last_log_complete &&
			!is_on_hold &&
			!doc.is_paused
		);

		let show_start = false,
			show_pause = false,
			show_resume = false,
			show_complete = false,
			is_timer_running = false;

		if (has_remaining_qty && materials_ready) {
			const manufactured_qty = doc.manufactured_qty || doc.total_completed_qty;
			const qty_yet_to_manufacture = doc.for_quantity - (manufactured_qty + doc.process_loss_qty);

			if (should_show_start) {
				show_start = true;
			} else if (doc.is_paused) {
				show_resume = true;
			} else if (qty_yet_to_manufacture > 0) {
				show_pause = true;
				show_complete = true;
				is_timer_running = true;
			}
		}

		// ── Timer color reflects job state ────────────────────────────────
		const [timer_color, timer_bg, timer_border] = [
			"var(--gray-600,#6b7280)",
			"var(--gray-100,#f3f4f6)",
			"var(--gray-300,#d1d5db)",
		];

		// ── Action button HTML ────────────────────────────────────────────
		const btn = (cls, icon_path, label, icon_color) => `
			<button class="btn btn-sm ${cls}" style="display:inline-flex;align-items:center;gap:5px;font-weight:600;padding:6px 14px;">
				${frappe.utils.icon(icon_path, "sm", "", "", "", "", icon_color)}
				${label}
			</button>`;

		const icons = {
			play: { d: '<polygon points="5 3 19 12 5 21 5 3"/>', fill: "currentColor", stroke: "none" },
			pause: {
				d: '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
				fill: "currentColor",
				stroke: "none",
			},
			check: { d: '<polyline points="20 6 9 17 4 12"/>', sw: 3 },
		};

		const buttons_html = [
			show_start && btn("btn-primary jcd-btn-start", "play", __("Start Job")),
			show_resume && btn("btn-primary jcd-btn-resume", "play", __("Resume Job")),
			show_pause && btn("btn-default jcd-btn-pause", "pause", __("Pause Job")),
			show_complete && btn("btn-primary jcd-btn-complete", "check", __("Complete Job"), "white"),
		]
			.filter(Boolean)
			.join("");

		// ── Render widget ─────────────────────────────────────────────────
		wrapper.append(`
			<div class="job-card-dashboard-widget"
				style="border:1px solid var(--border-color);border-radius:var(--border-radius-lg,8px);
					background:var(--card-bg,#fff);padding:16px 20px;margin-bottom:16px;">
				<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
					<div>
						<div style="font-size:10px;color:var(--text-muted);font-weight:600;
							text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">
							${__("Elapsed Time")}
						</div>
						<div style="display:flex;align-items:center;gap:8px;">
							${frappe.utils.icon("clock-4", "md", "", "", "", "", timer_color)}
							<span class="jcd-stopwatch"
								style="font-family:var(--monospace-font,'Courier New',monospace);
								font-size:28px;font-weight:700;letter-spacing:2px;color:${timer_color};">
								00:00:00
							</span>
						</div>
					</div>
					<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
						${buttons_html}
					</div>
				</div>
			</div>`);

		// ── Wire up button click handlers ─────────────────────────────────
		if (show_start) {
			wrapper.find(".jcd-btn-start").on("click", () => {
				const has_no_employee = !frm.doc.employee || !frm.doc.employee.length;

				if (has_no_employee) {
					// Capture the start time only when the employee dialog is submitted, not on click,
					// so the time spent selecting the operator is not counted as worked time.
>>>>>>> 808b2e2984 (fix: require material transfer before job card start and completion)
					frappe.prompt(
						{
							fieldtype: "Table MultiSelect",
							label: __("Select Employees"),
							options: "Job Card Time Log",
							fieldname: "employees",
						},
						(d) => {
							frm.events.start_job(frm, "Work In Progress", d.employees);
						},
						__("Assign Job to Employee")
					);
				} else {
					frm.events.start_job(frm, "Work In Progress", frm.doc.employee);
				}
			}).addClass("btn-primary");
		} else if (frm.doc.status == "On Hold") {
			frm.add_custom_button(__("Resume Job"), () => {
				frm.events.start_job(frm, "Resume Job", frm.doc.employee);
			}).addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Pause Job"), () => {
				frm.events.complete_job(frm, "On Hold");
			});

			frm.add_custom_button(__("Complete Job"), () => {
				var sub_operations = frm.doc.sub_operations;

				let set_qty = true;
				if (sub_operations && sub_operations.length > 1) {
					set_qty = false;
					let last_op_row = sub_operations[sub_operations.length - 2];

					if (last_op_row.status == "Complete") {
						set_qty = true;
					}
				}

				if (set_qty) {
					frappe.prompt(
						{
							fieldtype: "Float",
							label: __("Completed Quantity"),
							fieldname: "qty",
							default: frm.doc.for_quantity - frm.doc.total_completed_qty,
						},
						(data) => {
							frm.events.complete_job(frm, "Complete", data.qty);
						},
						__("Enter Value")
					);
				} else {
					frm.events.complete_job(frm, "Complete", 0.0);
				}
			}).addClass("btn-primary");
		}
	},

	start_job: function (frm, status, employee) {
		const args = {
			job_card_id: frm.doc.name,
			start_time: frappe.datetime.now_datetime(),
			employees: employee,
			status: status,
		};
		frm.events.make_time_log(frm, args);
	},

	complete_job: function (frm, status, completed_qty) {
		const args = {
			job_card_id: frm.doc.name,
			complete_time: frappe.datetime.now_datetime(),
			status: status,
			completed_qty: completed_qty,
		};
		frm.events.make_time_log(frm, args);
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
			var seconds = Math.floor(increment - hours * 3600 - minutes * 60);

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
		if (frm.doc.started_time || frm.doc.current_time) {
			if (frm.doc.status == "On Hold") {
				updateStopwatch(currentIncrement);
			} else {
				initialiseTimer();
			}
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
