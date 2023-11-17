// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Start',
			'Pick List': 'Create Pick List',
			'Job Card': 'Create Job Card'
		};

		// Set query for warehouses
		frm.set_query("wip_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("source_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("source_warehouse", "required_items", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("sales_order", function() {
			return {
				filters: {
					"status": ["not in", ["Closed", "On Hold"]]
				}
			};
		});

		frm.set_query("fg_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			};
		});

		frm.set_query("scrap_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			};
		});

		// Set query for BOM
		frm.set_query("bom_no", function() {
			if (frm.doc.production_item) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(frm.doc.production_item)}
				};
			} else {
				frappe.msgprint(__("Please enter Production Item first"));
			}
		});

		// Set query for FG Item
		frm.set_query("production_item", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {
					"is_stock_item": 1,
				}
			};
		});

		// Set query for FG Item
		frm.set_query("project", function() {
			return{
				filters:[
					['Project', 'status', 'not in', 'Completed, Cancelled']
				]
			};
		});

		frm.set_query("operation", "required_items", function() {
			return {
				query: "erpnext.manufacturing.doctype.work_order.work_order.get_bom_operations",
				filters: {
					'parent': frm.doc.bom_no,
					'parenttype': 'BOM'
				}
			};
		});

		// formatter for work order operation
		frm.set_indicator_formatter('operation',
			function(doc) { return (frm.doc.qty==doc.completed_qty) ? "green" : "orange"; });
	},

	onload: function(frm) {
		if (!frm.doc.status)
			frm.doc.status = 'Draft';

		frm.add_fetch("sales_order", "project", "project");

		if(frm.doc.__islocal) {
			frm.set_value({
				"actual_start_date": "",
				"actual_end_date": ""
			});
			erpnext.work_order.set_default_warehouse(frm);
		}
	},

	source_warehouse: function(frm) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.required_items, "source_warehouse", frm.doc.source_warehouse);
	},

	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.work_order.set_custom_buttons(frm);
		frm.set_intro("");

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.set_intro(__("Submit this Work Order for further processing."));
		} else {
			frm.trigger("show_progress_for_items");
			frm.trigger("show_progress_for_operations");
		}

		if (frm.doc.status != "Closed") {
			if (frm.doc.docstatus === 1 && frm.doc.status !== "Completed"
				&& frm.doc.operations && frm.doc.operations.length) {

				const not_completed = frm.doc.operations.filter(d => {
					if (d.status != 'Completed') {
						return true;
					}
				});

				if (not_completed && not_completed.length) {
					frm.add_custom_button(__('Create Job Card'), () => {
						frm.trigger("make_job_card");
					}).addClass('btn-primary');
				}
			}
		}

		if(frm.doc.required_items && frm.doc.allow_alternative_item) {
			const has_alternative = frm.doc.required_items.find(i => i.allow_alternative_item === 1);
			if (frm.doc.docstatus == 0 && has_alternative) {
				frm.add_custom_button(__('Alternate Item'), () => {
					erpnext.utils.select_alternate_items({
						frm: frm,
						child_docname: "required_items",
						warehouse_field: "source_warehouse",
						child_doctype: "Work Order Item",
						original_item_field: "original_item",
						condition: (d) => {
							if (d.allow_alternative_item) {return true;}
						}
					});
				});
			}
		}

		if (frm.doc.status == "Completed" &&
			frm.doc.__onload.backflush_raw_materials_based_on == "Material Transferred for Manufacture") {
			frm.add_custom_button(__('Create BOM'), () => {
				frm.trigger("make_bom");
			});
		}

		frm.trigger("add_custom_button_to_return_components");
	},

	add_custom_button_to_return_components: function(frm) {
		if (frm.doc.docstatus === 1 && in_list(["Closed", "Completed"], frm.doc.status)) {
			let non_consumed_items = frm.doc.required_items.filter(d =>{
				return flt(d.consumed_qty) < flt(d.transferred_qty - d.returned_qty)
			});

			if (non_consumed_items && non_consumed_items.length) {
				frm.add_custom_button(__("Return Components"), function() {
					frm.trigger("create_stock_return_entry");
				}).addClass("btn-primary");
			}
		}
	},

	create_stock_return_entry: function(frm) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.work_order.work_order.make_stock_return_entry",
			args: {
				"work_order": frm.doc.name,
			},
			callback: function(r) {
				if(!r.exc) {
					let doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				}
			}
		});
	},

	make_job_card: function(frm) {
		let qty = 0;
		let operations_data = [];

		const dialog = frappe.prompt({fieldname: 'operations', fieldtype: 'Table', label: __('Operations'),
			fields: [
				{
					fieldtype: 'Link',
					fieldname: 'operation',
					label: __('Operation'),
					read_only: 1,
					in_list_view: 1
				},
				{
					fieldtype: 'Link',
					fieldname: 'workstation',
					label: __('Workstation'),
					read_only: 1,
					in_list_view: 1
				},
				{
					fieldtype: 'Data',
					fieldname: 'name',
					label: __('Operation Id')
				},
				{
					fieldtype: 'Float',
					fieldname: 'pending_qty',
					label: __('Pending Qty'),
				},
				{
					fieldtype: 'Float',
					fieldname: 'qty',
					label: __('Quantity to Manufacture'),
					read_only: 0,
					in_list_view: 1,
				},
				{
					fieldtype: 'Float',
					fieldname: 'batch_size',
					label: __('Batch Size'),
					read_only: 1
				},
				{
					fieldtype: 'Int',
					fieldname: 'sequence_id',
					label: __('Sequence Id'),
					read_only: 1
				},
			],
			data: operations_data,
			in_place_edit: true,
			get_data: function() {
				return operations_data;
			}
		}, function(data) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.make_job_card",
				freeze: true,
				args: {
					work_order: frm.doc.name,
					operations: data.operations,
				},
				callback: function() {
					frm.reload_doc();
				}
			});
		}, __("Job Card"), __("Create"));

		dialog.fields_dict["operations"].grid.wrapper.find('.grid-add-row').hide();

		var pending_qty = 0;
		frm.doc.operations.forEach(data => {
			if(data.completed_qty + data.process_loss_qty != frm.doc.qty) {
				pending_qty = frm.doc.qty - flt(data.completed_qty) - flt(data.process_loss_qty);

				if (pending_qty) {
					dialog.fields_dict.operations.df.data.push({
						'name': data.name,
						'operation': data.operation,
						'workstation': data.workstation,
						'batch_size': data.batch_size,
						'qty': pending_qty,
						'pending_qty': pending_qty,
						'sequence_id': data.sequence_id
					});
				}
			}
		});
		dialog.fields_dict.operations.grid.refresh();
	},

	make_bom: function(frm) {
		frappe.call({
			method: "make_bom",
			doc: frm.doc,
			callback: function(r){
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		});
	},

	show_progress_for_items: function(frm) {
		var bars = [];
		var message = '';
		var added_min = false;

		// produced qty
		var title = __('{0} items produced', [frm.doc.produced_qty]);
		bars.push({
			'title': title,
			'width': (frm.doc.produced_qty / frm.doc.qty * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
			added_min = 0.5;
		}
		message = title;
		// pending qty
		if(!frm.doc.skip_transfer){
			var pending_complete = frm.doc.material_transferred_for_manufacturing - frm.doc.produced_qty;
			if(pending_complete) {
				var width = ((pending_complete / frm.doc.qty * 100) - added_min);
				title = __('{0} items in progress', [pending_complete]);
				bars.push({
					'title': title,
					'width': (width > 100 ? "99.5" : width)  + '%',
					'progress_class': 'progress-bar-warning'
				});
				message = message + '. ' + title;
			}
		}
		frm.dashboard.add_progress(__('Status'), bars, message);
	},

	show_progress_for_operations: function(frm) {
		if (frm.doc.operations && frm.doc.operations.length) {

			let progress_class = {
				"Work in Progress": "progress-bar-warning",
				"Completed": "progress-bar-success"
			};

			let bars = [];
			let message = '';
			let title = '';
			let status_wise_oprtation_data = {};
			let total_completed_qty = frm.doc.qty * frm.doc.operations.length;

			frm.doc.operations.forEach(d => {
				if (!status_wise_oprtation_data[d.status]) {
					status_wise_oprtation_data[d.status] = [d.completed_qty, d.operation];
				} else {
					status_wise_oprtation_data[d.status][0] += d.completed_qty;
					status_wise_oprtation_data[d.status][1] += ', ' + d.operation;
				}
			});

			for (let key in status_wise_oprtation_data) {
				title = __("{0} Operations: {1}", [key, status_wise_oprtation_data[key][1].bold()]);
				bars.push({
					'title': title,
					'width': status_wise_oprtation_data[key][0] / total_completed_qty * 100  + '%',
					'progress_class': progress_class[key]
				});

				message += title + '. ';
			}

			frm.dashboard.add_progress(__('Status'), bars, message);
		}
	},

	production_item: function(frm) {
		if (frm.doc.production_item) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_item_details",
				args: {
					item: frm.doc.production_item,
					project: frm.doc.project
				},
				freeze: true,
				callback: function(r) {
					if(r.message) {
						frm.set_value('sales_order', "");
						frm.trigger('set_sales_order');
						erpnext.in_production_item_onchange = true;

						$.each(["description", "stock_uom", "project", "bom_no", "allow_alternative_item",
							"transfer_material_against", "item_name"], function(i, field) {
							frm.set_value(field, r.message[field]);
						});

						if(r.message["set_scrap_wh_mandatory"]){
							frm.toggle_reqd("scrap_warehouse", true);
						}
						erpnext.in_production_item_onchange = false;
					}
				}
			});
		}
	},

	project: function(frm) {
		if(!erpnext.in_production_item_onchange && !frm.doc.bom_no) {
			frm.trigger("production_item");
		}
	},

	bom_no: function(frm) {
		return frm.call({
			doc: frm.doc,
			method: "get_items_and_operations_from_bom",
			freeze: true,
			callback: function(r) {
				if(r.message["set_scrap_wh_mandatory"]){
					frm.toggle_reqd("scrap_warehouse", true);
				}
			}
		});
	},

	use_multi_level_bom: function(frm) {
		if(frm.doc.bom_no) {
			frm.trigger("bom_no");
		}
	},

	qty: function(frm) {
		frm.trigger('bom_no');
	},

	before_submit: function(frm) {
		frm.fields_dict.required_items.grid.toggle_reqd("source_warehouse", true);
		frm.toggle_reqd("transfer_material_against",
			frm.doc.operations && frm.doc.operations.length > 0);
	},

	set_sales_order: function(frm) {
		if(frm.doc.production_item) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.query_sales_order",
				args: { production_item: frm.doc.production_item },
				callback: function(r) {
					frm.set_query("sales_order", function() {
						erpnext.in_production_item_onchange = true;
						return {
							filters: [
								["Sales Order","name", "in", r.message]
							]
						};
					});
				}
			});
		}
	},

	additional_operating_cost: function(frm) {
		erpnext.work_order.calculate_cost(frm.doc);
		erpnext.work_order.calculate_total_cost(frm);
	},
});

frappe.ui.form.on("Work Order Item", {
	source_warehouse: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(!row.item_code) {
			frappe.throw(__("Please set the Item Code first"));
		} else if(row.source_warehouse) {
			frappe.call({
				"method": "erpnext.stock.utils.get_latest_stock_qty",
				args: {
					item_code: row.item_code,
					warehouse: row.source_warehouse
				},
				callback: function (r) {
					frappe.model.set_value(row.doctype, row.name,
						"available_qty_at_source_warehouse", r.message);
				}
			});
		}
	},

	item_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.item_code) {
			frappe.call({
				method: "erpnext.stock.doctype.item.item.get_item_details",
				args: {
					item_code: row.item_code,
					company: frm.doc.company
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, {
							"required_qty": row.required_qty || 1,
							"item_name": r.message.item_name,
							"description": r.message.description,
							"source_warehouse": r.message.default_warehouse,
							"allow_alternative_item": r.message.allow_alternative_item,
							"include_item_in_manufacturing": r.message.include_item_in_manufacturing
						});
					}
				}
			});
		}
	}
});

frappe.ui.form.on("Work Order Operation", {
	workstation: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.workstation) {
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Workstation",
					name: d.workstation
				},
				callback: function (data) {
					frappe.model.set_value(d.doctype, d.name, "hour_rate", data.message.hour_rate);
					erpnext.work_order.calculate_cost(frm.doc);
					erpnext.work_order.calculate_total_cost(frm);
				}
			});
		}
	},
	time_in_mins: function(frm, cdt, cdn) {
		erpnext.work_order.calculate_cost(frm.doc);
		erpnext.work_order.calculate_total_cost(frm);
	},
});

erpnext.work_order = {
	set_custom_buttons: function(frm) {
		var doc = frm.doc;

		if (doc.status !== "Closed") {
			frm.add_custom_button(__('Close'), function() {
				frappe.confirm(__("Once the Work Order is Closed. It can't be resumed."),
					() => {
						erpnext.work_order.change_work_order_status(frm, "Closed");
					}
				);
			}, __("Status"));
		}

		if (doc.docstatus === 1 && !in_list(["Closed", "Completed"], doc.status)) {
			if (doc.status != 'Stopped' && doc.status != 'Completed') {
				frm.add_custom_button(__('Stop'), function() {
					erpnext.work_order.change_work_order_status(frm, "Stopped");
				}, __("Status"));
			} else if (doc.status == 'Stopped') {
				frm.add_custom_button(__('Re-open'), function() {
					erpnext.work_order.change_work_order_status(frm, "Resumed");
				}, __("Status"));
			}

			const show_start_btn = (frm.doc.skip_transfer
				|| frm.doc.transfer_material_against == 'Job Card') ? 0 : 1;

			if (show_start_btn) {
				let pending_to_transfer = frm.doc.required_items.some(
					item => flt(item.transferred_qty) < flt(item.required_qty)
				);
				if (pending_to_transfer && frm.doc.status != 'Stopped') {
					frm.has_start_btn = true;
					frm.add_custom_button(__('Create Pick List'), function() {
						erpnext.work_order.create_pick_list(frm);
					});
					var start_btn = frm.add_custom_button(__('Start'), function() {
						erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
					});
					start_btn.addClass('btn-primary');
				}
			}

			if (frm.doc.status != 'Stopped') {
				// If "Material Consumption is check in Manufacturing Settings, allow Material Consumption
				if (frm.doc.__onload && frm.doc.__onload.material_consumption == 1) {
					if (flt(doc.material_transferred_for_manufacturing) > 0 || frm.doc.skip_transfer) {
						// Only show "Material Consumption" when required_qty > consumed_qty
						var counter = 0;
						var tbl = frm.doc.required_items || [];
						var tbl_lenght = tbl.length;
						for (var i = 0, len = tbl_lenght; i < len; i++) {
							let wo_item_qty = frm.doc.required_items[i].transferred_qty || frm.doc.required_items[i].required_qty;
							if (flt(wo_item_qty) > flt(frm.doc.required_items[i].consumed_qty)) {
								counter += 1;
							}
						}
						if (counter > 0) {
							var consumption_btn = frm.add_custom_button(__('Material Consumption'), function() {
								const backflush_raw_materials_based_on = frm.doc.__onload.backflush_raw_materials_based_on;
								erpnext.work_order.make_consumption_se(frm, backflush_raw_materials_based_on);
							});
							consumption_btn.addClass('btn-primary');
						}
					}
				}

				if(!frm.doc.skip_transfer){
					if (flt(doc.material_transferred_for_manufacturing) > 0) {
						if ((flt(doc.produced_qty) < flt(doc.material_transferred_for_manufacturing))) {
							frm.has_finish_btn = true;

							var finish_btn = frm.add_custom_button(__('Finish'), function() {
								erpnext.work_order.make_se(frm, 'Manufacture');
							});

							if(doc.material_transferred_for_manufacturing>=doc.qty) {
								// all materials transferred for manufacturing, make this primary
								finish_btn.addClass('btn-primary');
							}
						} else if (frm.doc.__onload && frm.doc.__onload.overproduction_percentage) {
							let allowance_percentage = frm.doc.__onload.overproduction_percentage;

							if (allowance_percentage > 0) {
								let allowed_qty = frm.doc.qty + ((allowance_percentage / 100) * frm.doc.qty);

								if ((flt(doc.produced_qty) < allowed_qty)) {
									frm.add_custom_button(__('Finish'), function() {
										erpnext.work_order.make_se(frm, 'Manufacture');
									});
								}
							}
						}
					}
				} else {
					if ((flt(doc.produced_qty) < flt(doc.qty))) {
						var finish_btn = frm.add_custom_button(__('Finish'), function() {
							erpnext.work_order.make_se(frm, 'Manufacture');
						});
						finish_btn.addClass('btn-primary');
					}
				}
			}
		}
	},
	calculate_cost: function(doc) {
		if (doc.operations){
			var op = doc.operations;
			doc.planned_operating_cost = 0.0;
			for(var i=0;i<op.length;i++) {
				var planned_operating_cost = flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
				frappe.model.set_value('Work Order Operation', op[i].name,
					"planned_operating_cost", planned_operating_cost);
				doc.planned_operating_cost += planned_operating_cost;
			}
			refresh_field('planned_operating_cost');
		}
	},

	calculate_total_cost: function(frm) {
		let variable_cost = flt(frm.doc.actual_operating_cost) || flt(frm.doc.planned_operating_cost);
		frm.set_value("total_operating_cost", (flt(frm.doc.additional_operating_cost) + variable_cost));
	},

	set_default_warehouse: function(frm) {
		if (!(frm.doc.wip_warehouse || frm.doc.fg_warehouse)) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_default_warehouse",
				callback: function(r) {
					if (!r.exe) {
						frm.set_value("wip_warehouse", r.message.wip_warehouse);
						frm.set_value("fg_warehouse", r.message.fg_warehouse);
						frm.set_value("scrap_warehouse", r.message.scrap_warehouse);
					}
				}
			});
		}
	},

	get_max_transferable_qty: (frm, purpose) => {
		let max = 0;
		if (frm.doc.skip_transfer) {
			max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
		} else {
			if (purpose === 'Manufacture') {
				max = flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty);
			} else {
				max = flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
			}
		}
		return flt(max, precision('qty'));
	},

	show_prompt_for_qty_input: function(frm, purpose) {
		let max = this.get_max_transferable_qty(frm, purpose);
		return new Promise((resolve, reject) => {
			frappe.prompt({
				fieldtype: 'Float',
				label: __('Qty for {0}', [__(purpose)]),
				fieldname: 'qty',
				description: __('Max: {0}', [max]),
				default: max
			}, data => {
				max += (frm.doc.qty * (frm.doc.__onload.overproduction_percentage || 0.0)) / 100;

				if (data.qty > max) {
					frappe.msgprint(__('Quantity must not be more than {0}', [max]));
					reject();
				}
				data.purpose = purpose;
				resolve(data);
			}, __('Select Quantity'), __('Create'));
		});
	},

	make_se: function(frm, purpose) {
		this.show_prompt_for_qty_input(frm, purpose)
			.then(data => {
				return frappe.xcall('erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry', {
					'work_order_id': frm.doc.name,
					'purpose': purpose,
					'qty': data.qty
				});
			}).then(stock_entry => {
				frappe.model.sync(stock_entry);
				frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
			});

	},

	create_pick_list: function(frm, purpose='Material Transfer for Manufacture') {
		this.show_prompt_for_qty_input(frm, purpose)
			.then(data => {
				return frappe.xcall('erpnext.manufacturing.doctype.work_order.work_order.create_pick_list', {
					'source_name': frm.doc.name,
					'for_qty': data.qty
				});
			}).then(pick_list => {
				frappe.model.sync(pick_list);
				frappe.set_route('Form', pick_list.doctype, pick_list.name);
			});
	},

	make_consumption_se: function(frm, backflush_raw_materials_based_on) {
		if(!frm.doc.skip_transfer){
			var max = (backflush_raw_materials_based_on === "Material Transferred for Manufacture") ?
				flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty) :
				flt(frm.doc.qty) - flt(frm.doc.produced_qty);
				// flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
		} else {
			var max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
		}

		frappe.call({
			method:"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
			args: {
				"work_order_id": frm.doc.name,
				"purpose": "Material Consumption for Manufacture",
				"qty": max
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	change_work_order_status: function(frm, status) {
		let method_name = status=="Closed" ? "close_work_order" : "stop_unstop";
		frappe.call({
			method: `erpnext.manufacturing.doctype.work_order.work_order.${method_name}`,
			freeze: true,
			freeze_message: __("Updating Work Order status"),
			args: {
				work_order: frm.doc.name,
				status: status
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value("status", r.message);
					frm.reload_doc();
				}
			}
		});
	}
};

frappe.tour['Work Order'] = [
	{
		fieldname: "production_item",
		title: "Item to Manufacture",
		description: __("Select the Item to be manufactured.")
	},
	{
		fieldname: "bom_no",
		title: "BOM No",
		description: __("The default BOM for that item will be fetched by the system. You can also change the BOM.")
	},
	{
		fieldname: "qty",
		title: "Qty to Manufacture",
		description: __("Enter the quantity to manufacture. Raw material Items will be fetched only when this is set.")
	},
	{
		fieldname: "use_multi_level_bom",
		title: "Use Multi-Level BOM",
		description: __("This is enabled by default. If you want to plan materials for sub-assemblies of the Item you're manufacturing leave this enabled. If you plan and manufacture the sub-assemblies separately, you can disable this checkbox.")
	},
	{
		fieldname: "source_warehouse",
		title: "Source Warehouse",
		description: __("The warehouse where you store your raw materials. Each required item can have a separate source warehouse. Group warehouse also can be selected as source warehouse. On submission of the Work Order, the raw materials will be reserved in these warehouses for production usage.")
	},
	{
		fieldname: "fg_warehouse",
		title: "Target Warehouse",
		description: __("The warehouse where you store finished Items before they are shipped.")
	},
	{
		fieldname: "wip_warehouse",
		title: "Work-in-Progress Warehouse",
		description: __("The warehouse where your Items will be transferred when you begin production. Group Warehouse can also be selected as a Work in Progress warehouse.")
	},
	{
		fieldname: "scrap_warehouse",
		title: "Scrap Warehouse",
		description: __("If the BOM results in Scrap material, the Scrap Warehouse needs to be selected.")
	},
	{
		fieldname: "required_items",
		title: "Required Items",
		description: __("All the required items (raw materials) will be fetched from BOM and populated in this table. Here you can also change the Source Warehouse for any item. And during the production, you can track transferred raw materials from this table.")
	},
	{
		fieldname: "planned_start_date",
		title: "Planned Start Date",
		description: __("Set the Planned Start Date (an Estimated Date at which you want the Production to begin)")
	},
	{
		fieldname: "operations",
		title: "Operations",
		description: __("If the selected BOM has Operations mentioned in it, the system will fetch all Operations from BOM, these values can be changed.")
	},


];
