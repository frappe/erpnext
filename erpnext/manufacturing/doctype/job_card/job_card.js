// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Card", {
	setup: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["Quality Inspection"];

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
			const to_request = to_transfer && flt(frm.doc.requested_qty) < flt(frm.doc.for_quantity);

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

<<<<<<< HEAD
	setup_quality_inspection: function (frm) {
		let quality_inspection_field = frm.get_docfield("quality_inspection");
=======
	// Adds Material Request and Material Transfer buttons when items need to be transferred.
	setup_material_transfer_buttons(frm, has_items) {
		const { doc } = frm;

		if (frm.is_new() || doc.skip_material_transfer || doc.docstatus >= 2) return;

		const excess_transfer_allowed = doc.__onload.job_card_excess_transfer;
		const to_transfer =
			has_items && doc.items.some((row) => flt(row.transferred_qty) < flt(row.required_qty));
		const to_request = to_transfer && flt(doc.requested_qty) < flt(doc.for_quantity);

		if (has_items && (to_request || excess_transfer_allowed)) {
			frm.add_custom_button(
				__("Material Request"),
				() => frm.trigger("make_material_request"),
				__("Create")
			);
		}

		if (has_items && (to_transfer || excess_transfer_allowed)) {
			frm.add_custom_button(
				__("Material Transfer"),
				() => frm.trigger("make_stock_entry"),
				__("Create")
			);
		}
	},

	keep_one_primary_button(frm) {
		const dashboard = $(frm.fields_dict["job_card_dashboard"].wrapper);
		const has_primary = !!dashboard.find(".btn-primary").length;
		frappe.ui.button
			.dress(frm.page.btn_primary, { variant: has_primary ? "subtle" : "solid" })
			.toggleClass("btn-primary", !has_primary);
	},

	hold_submit_until_job_is_done(frm, has_items) {
		if (frm.doc.docstatus !== 0 || frm.is_new() || frm.is_dirty()) return;

		const steps = frm.events.get_job_steps(frm, has_items);
		if (steps.slice(0, -1).some((step) => !step.done)) {
			frm.page.clear_primary_action();
			frm.dashboard.clear_headline();
		}
	},

	get_job_steps(frm, has_items) {
		const { doc } = frm;
		const needs_move = has_items && !doc.skip_material_transfer && !doc.is_corrective_job_card;
		const steps = [];

		if (needs_move) {
			steps.push({
				label: __("Move Materials"),
				done: !doc.items.some((row) => flt(row.transferred_qty) < flt(row.required_qty)),
			});
		}

		steps.push(
			{ label: __("Start Job"), done: !!doc.time_logs?.length },
			{ label: __("Complete Job"), done: frm.events.is_job_done(frm) },
			{ label: __("Submit"), done: false }
		);

		return steps;
	},

	is_job_done(frm) {
		const { doc } = frm;
		const last_log = doc.time_logs?.[doc.time_logs.length - 1];
		const qty_precision = precision("for_quantity", doc);
		const accounted_qty = flt(doc.total_completed_qty) + flt(doc.process_loss_qty) + flt(doc.pending_qty);
		const needs_end_time = !!doc.__onload?.enforce_time_logs;

		return (
			!!last_log &&
			(!needs_end_time || !!last_log.to_time) &&
			flt(doc.for_quantity) > 0 &&
			flt(accounted_qty, qty_precision) >= flt(doc.for_quantity, qty_precision)
		);
	},

	get_job_steps_html(frm, has_items) {
		const steps = frm.events.get_job_steps(frm, has_items);
		const current = steps.find((step) => !step.done);

		const pills = steps
			.map((step, idx) => {
				const color = step.done ? "green" : step === current ? "blue" : "gray";
				const mark = step.done ? "✓" : `${idx + 1}.`;
				return `<span class="indicator-pill no-indicator-dot ${color}" style="flex-shrink:0;">${mark} ${step.label}</span>`;
			})
			.join(`<span class="text-muted" style="flex-shrink:0;">›</span>`);

		return `<div style="display:flex;align-items:center;gap:6px;overflow-x:auto;margin-bottom:16px;">${pills}</div>`;
	},

	move_materials(frm) {
		frm.call({ method: "get_material_shortages", doc: frm.doc, freeze: true }).then(({ message }) => {
			if (!message?.length) {
				frm.trigger("make_stock_entry");
				return;
			}

			frm.events.show_shortage_dialog(frm, message);
		});
	},

	show_shortage_dialog(frm, shortages) {
		const escape = frappe.utils.escape_html;
		const qty_precision = precision("for_quantity", frm.doc);
		const qty = (value, uom) => `${format_number(value, null, qty_precision)} ${escape(uom || "")}`;
		const rows = shortages
			.map(
				(row) => `<tr>
					<td class="ellipsis">${escape(row.item_code)}</td>
					<td class="ellipsis">${escape(row.warehouse)}</td>
					<td class="text-right">${qty(row.qty_to_move, row.uom)}</td>
					<td class="text-right">${qty(row.available_qty, row.uom)}</td>
					<td class="text-right text-danger">${qty(row.shortage_qty, row.uom)}</td>
				</tr>`
			)
			.join("");

		const dialog = new frappe.ui.Dialog({
			title: __("Not Enough Stock"),
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "shortages",
					options: `<p>${__(
						"These raw materials are short in their source warehouse, so the transfer cannot be submitted yet."
					)}</p>
						<table class="table table-bordered" style="table-layout:fixed;">
							<thead><tr>
								<th>${__("Item")}</th>
								<th>${__("Source Warehouse")}</th>
								<th class="text-right">${__("To Move")}</th>
								<th class="text-right">${__("In Stock")}</th>
								<th class="text-right">${__("Short")}</th>
							</tr></thead>
							<tbody>${rows}</tbody>
						</table>`,
				},
			],
			primary_action_label: __("Request Missing Materials"),
			primary_action() {
				dialog.hide();
				frm.events.make_material_request(frm, true);
			},
			secondary_action_label: __("Continue to Transfer"),
			secondary_action() {
				dialog.hide();
				frm.trigger("make_stock_entry");
			},
		});
		dialog.show();
	},

	// Renders the dashboard widget (info + timer + action buttons) into job_card_dashboard wrapper.
	// Returns true if the job timer is actively running, so the caller can skip the stock entry button.
	setup_job_action_buttons(frm, has_items) {
		return frm.events.make_dashboard(frm, has_items);
	},

	complete_job_card(frm) {
		let pending_qty = flt(
			frm.doc.for_quantity - frm.doc.total_completed_qty - frm.doc.process_loss_qty,
			precision("for_quantity", frm.doc)
		);
		if (frm.doc.pending_qty > 0) {
			pending_qty = frm.doc.pending_qty;
		}
		const completed_qty = get_completable_qty(frm, pending_qty);

		const fields = [
			{
				fieldtype: "Float",
				label: __("Qty to Manufacture in this Cycle"),
				fieldname: "for_quantity",
				reqd: 1,
				default: pending_qty,
				description: __("Completed, Pending and Process Loss quantities must add up to this."),
				change() {
					const dialog = frm.job_completion_dialog;
					const for_quantity = dialog.get_value("for_quantity");
					const completed_qty = get_completable_qty(frm, for_quantity);
					dialog.set_value("completed_qty", completed_qty);
					dialog.set_value("pending_qty", for_quantity - completed_qty);
					dialog.set_value("process_loss_qty", 0);
				},
			},
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "completed_qty",
				default: completed_qty,
				change() {
					const dialog = frm.job_completion_dialog;
					const remaining =
						dialog.get_value("for_quantity") -
						dialog.get_value("completed_qty") -
						dialog.get_value("process_loss_qty");

					if (remaining < 0) {
						const max_completed_qty =
							flt(dialog.get_value("for_quantity")) - flt(dialog.get_value("process_loss_qty"));
						dialog.set_value("completed_qty", max_completed_qty);
						frappe.throw(
							__("Completed Quantity cannot be greater than {0}", [
								get_qty_with_uom(max_completed_qty, frm.doc.stock_uom),
							])
						);
					}

					if (remaining != dialog.get_value("pending_qty")) {
						dialog.set_value("pending_qty", remaining);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Pending Quantity"),
				fieldname: "pending_qty",
				default: pending_qty - completed_qty,
				description: __("Qty left for a later cycle or for another job card."),
				change() {
					const dialog = frm.job_completion_dialog;
					const process_loss_qty =
						dialog.get_value("for_quantity") -
						dialog.get_value("completed_qty") -
						dialog.get_value("pending_qty");

					if (process_loss_qty < 0) {
						dialog.set_value("pending_qty", 0);
						frappe.throw(
							__("Pending Quantity cannot be greater than {0}", [
								get_qty_with_uom(
									flt(dialog.get_value("for_quantity")) -
										flt(dialog.get_value("completed_qty")),
									frm.doc.stock_uom
								),
							])
						);
					}

					if (process_loss_qty != dialog.get_value("process_loss_qty")) {
						dialog.set_value("process_loss_qty", process_loss_qty);
					}
				},
			},
			{
				fieldtype: "Float",
				label: __("Process Loss Quantity"),
				fieldname: "process_loss_qty",
				description: __("Qty scrapped in this cycle, nobody will produce it."),
				onchange() {
					const dialog = frm.job_completion_dialog;
					const remaining =
						dialog.get_value("for_quantity") -
						dialog.get_value("completed_qty") -
						dialog.get_value("process_loss_qty");

					if (remaining < 0) {
						dialog.set_value("process_loss_qty", 0);
						frappe.throw(
							__("Process Loss Quantity cannot be greater than {0}", [
								get_qty_with_uom(
									flt(dialog.get_value("for_quantity")) -
										flt(dialog.get_value("completed_qty")),
									frm.doc.stock_uom
								),
							])
						);
					}

					if (remaining != dialog.get_value("pending_qty")) {
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
					const target_qty = flt(
						frm.doc.for_quantity - frm.doc.process_loss_qty,
						precision("for_quantity", frm.doc)
					);
					const pending = frm.doc.sub_operations.filter((d) => flt(d.completed_qty) < target_qty);
					return {
						filters: { name: ["in", pending.map((d) => d.sub_operation)] },
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
				default: frappe.datetime.system_datetime(),
			});
		}

		frm.job_completion_dialog = frappe.prompt(
			fields,
			(data) => {
				if (data.completed_qty < 0) {
					frappe.throw(__("Completed Quantity cannot be negative"));
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
			__("Complete Job"),
			__("Update")
		);
	},

	make_subcontracting_po(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.for_quantity > frm.doc.manufactured_qty) {
			frm.add_custom_button(__("Make Subcontracting PO"), () => {
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.job_card.mapper.make_subcontracting_po",
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

	setup_quality_inspection(frm) {
		const quality_inspection_field = frm.get_docfield("quality_inspection");
>>>>>>> ec7b52e (fix(manufacturing): log job card times in the system time zone)
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

		const transfer_pending =
			!frm.doc.is_corrective_job_card &&
			(frm.doc.items || []).length &&
			flt(frm.doc.transferred_qty) < flt(frm.doc.for_quantity);

		if (!frm.doc.started_time && !frm.doc.current_time) {
			if (transfer_pending) {
				return;
			}

			frm.add_custom_button(__("Start Job"), () => {
				if ((frm.doc.employee && !frm.doc.employee.length) || !frm.doc.employee) {
					frappe.prompt(
						{
							fieldtype: "Table MultiSelect",
							label: __("Select Employees"),
							options: "Job Card Time Log",
							fieldname: "employees",
						},
<<<<<<< HEAD
						(d) => {
							frm.events.start_job(frm, "Work In Progress", d.employees);
						},
						__("Assign Job to Employee")
					);
				} else {
					frm.events.start_job(frm, "Work In Progress", frm.doc.employee);
=======
						(d) => frm.events.start_timer(frm, frappe.datetime.system_datetime(), d.employees),
						__("Assign Job to Employee")
					);
				} else {
					frm.events.start_timer(frm, frappe.datetime.system_datetime(), frm.doc.employee);
>>>>>>> ec7b52e (fix(manufacturing): log job card times in the system time zone)
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

<<<<<<< HEAD
			frm.add_custom_button(__("Complete Job"), () => {
				var sub_operations = frm.doc.sub_operations;

				let set_qty = true;
				if (sub_operations && sub_operations.length > 1) {
					set_qty = false;
					let last_op_row = sub_operations[sub_operations.length - 2];
=======
		if (show_resume) {
			wrapper.find(".jcd-btn-resume").on("click", () => {
				frm.call({
					method: "resume_job",
					doc: frm.doc,
					args: { start_time: frappe.datetime.system_datetime() },
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
					args: { end_time: frappe.datetime.system_datetime() },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}
>>>>>>> ec7b52e (fix(manufacturing): log job card times in the system time zone)

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
							if (data.qty < 0) {
								frappe.throw(__("Completed Quantity cannot be negative"));
							}

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
				current_time += get_seconds_diff(frappe.datetime.system_datetime(), d.from_time);
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
