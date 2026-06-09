// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Card", {
	setup(frm) {
		frm.set_query("operation", () => ({
			query: "erpnext.manufacturing.doctype.job_card.job_card.get_operations",
			filters: { work_order: frm.doc.work_order },
		}));

		frm.set_query("serial_and_batch_bundle", () => ({
			filters: {
				item_code: frm.doc.production_item,
				voucher_type: frm.doc.doctype,
				voucher_no: ["in", [frm.doc.name, ""]],
				is_cancelled: 0,
			},
		}));

		frm.set_query("item_code", "secondary_items", () => ({
			filters: { disabled: 0 },
		}));

		frm.set_query("operation", "time_logs", () => {
			const operations = (frm.doc.sub_operations || []).map((d) => d.sub_operation);
			return { filters: { name: ["in", operations] } };
		});

		frm.set_query("work_order", () => ({
			filters: { status: ["not in", ["Cancelled", "Closed", "Stopped"]] },
		}));

		frm.events.set_company_filters(frm, "target_warehouse");
		frm.events.set_company_filters(frm, "source_warehouse");
		frm.events.set_company_filters(frm, "wip_warehouse");

		frm.set_query("source_warehouse", "items", () => ({
			filters: { company: frm.doc.company },
		}));

		frm.set_indicator_formatter("sub_operation", (doc) => {
			if (doc.status === "Pending") return "red";
			return doc.status === "Complete" ? "green" : "orange";
		});

		frm.set_query("employee", () => ({
			filters: {
				company: frm.doc.company,
				status: "Active",
			},
		}));
	},

	pending_qty(frm) {
		if (frm.doc.total_completed_qty <= 0.0) {
			frm.doc.pending_qty = 0.0;
			refresh_field("pending_qty");
			frappe.throw(__("Please complete the job first before entering Pending Quantity"));
		}

		if (frm.doc.pending_qty < 0) {
			frappe.throw(__("Pending Quantity cannot be less than 0"));
		}

		const remaining_qty = flt(frm.doc.for_quantity) - flt(frm.doc.total_completed_qty);

		if (remaining_qty < frm.doc.pending_qty) {
			frm.doc.pending_qty = 0.0;
			refresh_field("pending_qty");
			frappe.throw(__("Pending Quantity cannot be greater than {0}", [remaining_qty]));
		}

		const process_loss_qty = flt(remaining_qty) - flt(frm.doc.pending_qty);
		frm.doc.process_loss_qty = process_loss_qty >= 0 ? process_loss_qty : 0;
		refresh_field("process_loss_qty");
	},

	set_company_filters(frm, fieldname) {
		frm.set_query(fieldname, () => ({
			filters: { company: frm.doc.company },
		}));
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
		const { doc } = frm;
		const can_make_stock_entry =
			doc.track_semi_finished_goods &&
			doc.docstatus === 1 &&
			!doc.is_subcontracted &&
			(doc.skip_material_transfer || doc.transferred_qty > 0) &&
			flt(doc.manufactured_qty) + flt(doc.process_loss_qty) < flt(doc.for_quantity);

		if (!can_make_stock_entry) return;

		frm.add_custom_button(__("Make Stock Entry"), () => {
			frappe.confirm(
				__("Do you want to submit the stock entry?"),
				() => frm.events.make_manufacture_stock_entry(frm, 1),
				() => frm.events.make_manufacture_stock_entry(frm, 0)
			);
		}).addClass("btn-primary");
	},

	make_manufacture_stock_entry(frm, submit_entry) {
		frm.call({
			method: "make_stock_entry_for_semi_fg_item",
			args: { auto_submit: submit_entry },
			doc: frm.doc,
			freeze: true,
			callback() {
				frm.reload_doc();
			},
		});
	},

	refresh(frm) {
		const { doc } = frm;
		const has_items = doc.items && doc.items.length;

		// Clear any running timer tick from a previous render.
		if (frm._jcd_timer_interval) {
			clearInterval(frm._jcd_timer_interval);
			frm._jcd_timer_interval = null;
		}

		frm.trigger("make_fields_read_only");

		if (!frm.is_new() && doc.__onload?.work_order_closed) {
			frm.disable_save();
			return;
		}

		if (doc.is_subcontracted) {
			frm.trigger("make_subcontracting_po");
			return;
		}

		if (doc.docstatus > 0) {
			frm.set_df_property("pending_qty", "read_only", 1);
		}

		const has_stock_entry = !!doc.__onload?.has_stock_entry;
		frm.toggle_enable("for_quantity", !has_stock_entry);

		if (doc.docstatus != 0) {
			frm.fields_dict["time_logs"].grid.update_docfield_property("completed_qty", "read_only", 1);
			frm.fields_dict["time_logs"].grid.update_docfield_property("time_in_mins", "read_only", 1);
		}

		frm.events.setup_material_transfer_buttons(frm, has_items);

		if (doc.docstatus == 1 && !doc.is_corrective_job_card && !doc.finished_good) {
			frm.trigger("setup_corrective_job_card");
		}

		frm.set_query("quality_inspection", () => ({
			query: "erpnext.stock.doctype.quality_inspection.quality_inspection.quality_inspection_query",
			filters: {
				item_code: doc.production_item,
				reference_name: doc.name,
			},
		}));

		frm.trigger("toggle_operation_number");

		const is_timer_running = frm.events.setup_job_action_buttons(frm, has_items);

		if (!is_timer_running) {
			frm.trigger("setup_stock_entry");
		}

		frm.trigger("setup_quality_inspection");

		if (doc.work_order) {
			frappe.db.get_value("Work Order", doc.work_order, "transfer_material_against").then((r) => {
				if (r.message.transfer_material_against == "Work Order" && !doc.operation_row_id) {
					frm.set_df_property("items", "hidden", 1);
				}
			});
		}

		const sbb_field = frm.get_docfield("serial_and_batch_bundle");
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = () => ({
				item_code: doc.production_item,
				warehouse: doc.wip_warehouse,
				voucher_type: doc.doctype,
			});
		}
	},

	// Adds Material Request and Material Transfer buttons when items need to be transferred.
	setup_material_transfer_buttons(frm, has_items) {
		const { doc } = frm;

		if (frm.is_new() || doc.skip_material_transfer || doc.docstatus >= 2) return;

		const excess_transfer_allowed = doc.__onload.job_card_excess_transfer;
		const to_request = doc.for_quantity > doc.transferred_qty;

		if (has_items && (to_request || excess_transfer_allowed)) {
			frm.add_custom_button(
				__("Material Request"),
				() => frm.trigger("make_material_request"),
				__("Create")
			);
		}

		// check if any row has untransferred materials in case of multiple items in JC
		const to_transfer = doc.items.some((row) => row.transferred_qty < row.required_qty);

		if (has_items && (to_transfer || excess_transfer_allowed)) {
			frm.add_custom_button(
				__("Material Transfer"),
				() => frm.trigger("make_stock_entry"),
				__("Create")
			);
		}
	},

	// Renders the dashboard widget (info + timer + action buttons) into job_card_dashboard wrapper.
	// Returns true if the job timer is actively running, so the caller can skip the stock entry button.
	setup_job_action_buttons(frm, has_items) {
		return frm.events.make_dashboard(frm, has_items);
	},

	complete_job_card(frm) {
		let pending_qty = frm.doc.for_quantity - frm.doc.total_completed_qty;
		if (frm.doc.pending_qty > 0) {
			pending_qty = frm.doc.pending_qty;
		}

		const fields = [
			{
				fieldtype: "Float",
				label: __("Qty to Manufacture"),
				fieldname: "for_quantity",
				reqd: 1,
				default: pending_qty,
				change() {
					const dialog = frm.job_completion_dialog;
					dialog.set_value("completed_qty", dialog.get_value("for_quantity"));
					dialog.set_value("process_loss_qty", 0);
				},
			},
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "completed_qty",
				reqd: 1,
				default: pending_qty,
				change() {
					const dialog = frm.job_completion_dialog;
					const remaining = dialog.get_value("for_quantity") - dialog.get_value("completed_qty");
					if (remaining > 0 && remaining != dialog.get_value("pending_qty")) {
						dialog.set_value("pending_qty", remaining);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Pending Quantity"),
				fieldname: "pending_qty",
				default: 0.0,
				change() {
					const dialog = frm.job_completion_dialog;
					const process_loss_qty =
						dialog.get_value("for_quantity") -
						dialog.get_value("completed_qty") -
						dialog.get_value("pending_qty");
					if (process_loss_qty >= 0 && process_loss_qty != dialog.get_value("process_loss_qty")) {
						dialog.set_value("process_loss_qty", process_loss_qty);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Process Loss Quantity"),
				fieldname: "process_loss_qty",
				onchange() {
					const dialog = frm.job_completion_dialog;
					const remaining =
						dialog.get_value("for_quantity") -
						dialog.get_value("completed_qty") -
						dialog.get_value("process_loss_qty");
					if (remaining >= 0 && remaining != dialog.get_value("pending_qty")) {
						dialog.set_value("pending_qty", remaining);
					}
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
					const non_completed = frm.doc.sub_operations.filter((d) => d.status === "Pending");
					return {
						filters: { name: ["in", non_completed.map((d) => d.sub_operation)] },
					};
				},
				reqd: 1,
			});
		}

		const last_completed_row = get_last_completed_row(frm.doc.time_logs);
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
						pending_qty: data.pending_qty,
						process_loss_qty: data.process_loss_qty,
						end_time: data.end_time,
						sub_operation: data.sub_operation,
					},
					callback() {
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
			args: { start_time, employees },
			callback() {
				frm.reload_doc();
			},
		});
	},

	make_finished_good(frm) {
		const fields = [
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
					args: { qty: data.qty, end_time: data.end_time },
					callback(r) {
						const doc = frappe.model.sync(r.message);
						frappe.set_route("Form", doc[0].doctype, doc[0].name);
					},
				});
			},
			__("Enter Value"),
			__("Update"),
			__("Set Finished Good Quantity")
		);
	},

	setup_quality_inspection(frm) {
		const quality_inspection_field = frm.get_docfield("quality_inspection");
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

	setup_corrective_job_card(frm) {
		frm.add_custom_button(
			__("Corrective Job Card"),
			() => {
				const operations = frm.doc.sub_operations
					.map((d) => d.sub_operation)
					.concat(frm.doc.operation);

				const fields = [
					{
						fieldtype: "Link",
						label: __("Corrective Operation"),
						options: "Operation",
						fieldname: "operation",
						get_query() {
							return { filters: { is_corrective_operation: 1 } };
						},
					},
					{
						fieldtype: "Link",
						label: __("For Operation"),
						options: "Operation",
						fieldname: "for_operation",
						get_query() {
							return { filters: { name: ["in", operations] } };
						},
					},
				];

				frappe.prompt(
					fields,
					(d) => frm.events.make_corrective_job_card(frm, d.operation, d.for_operation),
					__("Select Corrective Operation")
				);
			},
			__("Make")
		);
	},

	make_corrective_job_card(frm, operation, for_operation) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_corrective_job_card",
			args: {
				source_name: frm.doc.name,
				operation: operation,
				for_operation: for_operation,
			},
			callback(r) {
				if (r.message) {
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			},
		});
	},

	operation(frm) {
		frm.trigger("toggle_operation_number");

		if (frm.doc.operation && frm.doc.work_order) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.job_card.job_card.get_operation_details",
				args: {
					work_order: frm.doc.work_order,
					operation: frm.doc.operation,
				},
				callback(r) {
					if (!r.message) return;

					if (r.message.length == 1) {
						frm.set_value("operation_id", r.message[0].name);
					} else {
						const args = r.message.map((row) => ({ label: row.idx, value: row.name }));
						const description = __("Operation {0} added multiple times in the work order {1}", [
							frm.doc.operation,
							frm.doc.work_order,
						]);
						frm.set_df_property("operation_row_number", "options", args);
						frm.set_df_property("operation_row_number", "description", description);
					}

					frm.trigger("toggle_operation_number");
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

	make_time_log(frm, args) {
		frm.events.update_sub_operation(frm, args);

		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_time_log",
			args: { args },
			freeze: true,
			callback() {
				frm.reload_doc();
				frm.trigger("make_dashboard");
			},
		});
	},

	update_sub_operation(frm, args) {
		if (frm.doc.sub_operations?.length) {
			const pending_sub_ops = frm.doc.sub_operations.filter((d) => d.status != "Complete");
			if (pending_sub_ops.length) {
				args["sub_operation"] = pending_sub_ops[0].sub_operation;
			}
		}
	},

	make_dashboard(frm, has_items) {
		if (frm.doc.__islocal) return false;

		frm.dashboard.refresh();

		// Clear any previously running timer tick before re-rendering.
		if (frm._jcd_timer_interval) {
			clearInterval(frm._jcd_timer_interval);
			frm._jcd_timer_interval = null;
		}

		const wrapper = $(frm.fields_dict["job_card_dashboard"].wrapper);
		wrapper.empty();

		if (frm.doc.docstatus !== 0) {
			return;
		}

		const { doc } = frm;
		const { time_logs, status } = doc;

		// ── Determine which action buttons to show ────────────────────────
		const has_remaining_qty = doc.for_quantity + doc.process_loss_qty > doc.total_completed_qty;
		const materials_ready =
			doc.skip_material_transfer ||
			doc.transferred_qty >= doc.for_quantity + doc.process_loss_qty ||
			!doc.finished_good ||
			!has_items?.length;

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
				const from_time = frappe.datetime.now_datetime();
				const has_no_employee = !frm.doc.employee || !frm.doc.employee.length;

				if (has_no_employee) {
					frappe.prompt(
						{
							fieldtype: "Table MultiSelect",
							label: __("Select Employees"),
							options: "Job Card Time Log",
							fieldname: "employees",
							reqd: 1,
							filters: { status: "Active" },
						},
						(d) => frm.events.start_timer(frm, from_time, d.employees),
						__("Assign Job to Employee")
					);
				} else {
					frm.events.start_timer(frm, from_time, frm.doc.employee);
				}
			});
		}

		if (show_resume) {
			wrapper.find(".jcd-btn-resume").on("click", () => {
				frm.call({
					method: "resume_job",
					doc: frm.doc,
					args: { start_time: frappe.datetime.now_datetime() },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}

		if (show_pause) {
			wrapper.find(".jcd-btn-pause").on("click", () => {
				frm.call({
					method: "pause_job",
					doc: frm.doc,
					args: { end_time: frappe.datetime.now_datetime() },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}

		if (show_complete) {
			wrapper.find(".jcd-btn-complete").on("click", () => {
				frm.trigger("complete_job_card");
			});
		}

		// ── Timer tick ────────────────────────────────────────────────────
		const timer_el = wrapper.find(".jcd-stopwatch");
		const pad = (n) => String(n).padStart(2, "0");
		const update_stopwatch = (secs) => {
			const h = Math.floor(secs / 3600);
			const m = Math.floor((secs % 3600) / 60);
			const s = Math.floor(secs % 60);
			timer_el.text(`${pad(h)}:${pad(m)}:${pad(s)}`);
		};

		let current_increment = frm.events.get_current_time(frm);
		update_stopwatch(current_increment);

		if (is_actively_running) {
			frm._jcd_timer_interval = setInterval(() => {
				current_increment += 1;
				update_stopwatch(current_increment);
			}, 1000);
		}

		// Demote Submit to btn-default when an action button is already primary.
		const has_action_button = show_start || show_resume || show_complete;
		if (frm.page.btn_primary) {
			frm.page.btn_primary
				.toggleClass("btn-primary", !has_action_button)
				.toggleClass("btn-default", has_action_button);
		}

		return is_timer_running;
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

	hide_timer(frm) {
		if (frm._jcd_timer_interval) {
			clearInterval(frm._jcd_timer_interval);
			frm._jcd_timer_interval = null;
		}
		$(frm.fields_dict["job_card_dashboard"].wrapper).empty();
	},

	for_quantity(frm) {
		frm.doc.items = [];
		frm.call({
			method: "get_required_items",
			doc: frm.doc,
			callback() {
				refresh_field("items");
			},
		});
	},

	make_material_request(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_material_request",
			frm: frm,
			run_link_triggers: true,
		});
	},

	make_stock_entry(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
			frm: frm,
			run_link_triggers: true,
		});
	},

	set_total_completed_qty(frm) {
		frm.doc.total_completed_qty = 0;
		frm.doc.time_logs.forEach((d) => {
			if (d.completed_qty) {
				frm.doc.total_completed_qty += d.completed_qty;
			}
		});

		if (frm.doc.total_completed_qty && frm.doc.for_quantity > frm.doc.total_completed_qty) {
			const flt_precision = precision("for_quantity", frm.doc);
			const process_loss_qty =
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
	completed_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.completed_qty) {
			frappe.model.set_value(row.doctype, row.name, {
				time_in_mins: 0,
				to_time: "",
			});
		}

		frm.events.set_total_completed_qty(frm);
	},
});

function get_seconds_diff(d1, d2) {
	return moment(d1).diff(d2, "seconds");
}

function get_last_completed_row(time_logs) {
	const completed_rows = time_logs.filter((d) => d.to_time);
	return completed_rows[completed_rows.length - 1];
}

function get_last_row(time_logs) {
	return time_logs[time_logs.length - 1] || {};
}
