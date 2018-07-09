// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Make Stock Entry',
		}

		// Set query for warehouses
		frm.set_query("wip_warehouse", function(doc) {
			return {
				filters: {
					'company': frm.doc.company,
				}
			}
		});

		frm.set_query("source_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			}
		});

		frm.set_query("source_warehouse", "required_items", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			}
		});

		frm.set_query("fg_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			}
		});

		frm.set_query("scrap_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			}
		});

		// Set query for BOM
		frm.set_query("bom_no", function() {
			if (frm.doc.production_item) {
				return{
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(frm.doc.production_item)}
				}
			} else msgprint(__("Please enter Production Item first"));
		});

		// Set query for FG Item
		frm.set_query("production_item", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:{
					'is_stock_item': 1,
				}
			}
		});

		// Set query for FG Item
		frm.set_query("project", function() {
			return{
				filters:[
					['Project', 'status', 'not in', 'Completed, Cancelled']
				]
			}
		});

		// formatter for work order operation
		frm.set_indicator_formatter('operation',
			function(doc) { return (frm.doc.qty==doc.completed_qty) ? "green" : "orange" });
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

	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.work_order.set_custom_buttons(frm);
		frm.set_intro("");

		if (frm.doc.docstatus === 0 && !frm.doc.__islocal) {
			frm.set_intro(__("Submit this Work Order for further processing."));
		}

		if (frm.doc.docstatus===1) {
			frm.trigger('show_progress');
		}

		if (frm.doc.docstatus === 1
			&& frm.doc.operations && frm.doc.operations.length
			&& frm.doc.qty != frm.doc.material_transferred_for_manufacturing) {

			const not_completed = frm.doc.operations.filter(d => {
				if(d.status != 'Completed') {
					return true;
				}
			});

			if(not_completed && not_completed.length) {
				frm.add_custom_button(__('Create Job Card'), () => {
					frm.trigger("make_job_card")
				}).addClass('btn-primary');
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
					})
				});
			}
		}

		if (frm.doc.status == "Completed" &&
			frm.doc.__onload.backflush_raw_materials_based_on == "Material Transferred for Manufacture") {
			frm.add_custom_button(__('Create BOM'), () => {
				frm.trigger("make_bom");
			});
		}
	},

	make_job_card: function(frm) {
		let qty = 0;
		const fields = [{
			fieldtype: "Link",
			fieldname: "operation",
			options: "Operation",
			label: __("Operation"),
			get_query: () => {
				const filter_workstation = frm.doc.operations.filter(d => {
					if (d.status != "Completed") {
						return d;
					}
				});

				return {
					filters: {
						name: ["in", (filter_workstation || []).map(d => d.operation)]
					}
				};
			},
			reqd: true
		}, {
			fieldtype: "Link",
			fieldname: "workstation",
			options: "Workstation",
			label: __("Workstation"),
			get_query: () => {
				const operation = dialog.get_value("operation");
				const filter_workstation = frm.doc.operations.filter(d => {
					if (d.operation == operation) {
						return d;
					}
				});

				return {
					filters: {
						name: ["in", (filter_workstation || []).map(d => d.workstation)]
					}
				};
			},
			onchange: () => {
				const operation = dialog.get_value("operation");
				const workstation = dialog.get_value("workstation");
				if (operation && workstation) {
					const row = frm.doc.operations.filter(d => d.operation == operation && d.workstation == workstation)[0];
					qty = frm.doc.qty - row.completed_qty;

					if (qty > 0) {
						dialog.set_value("qty", qty);
					}
				}
			},
			reqd: true
		}, {
			fieldtype: "Float",
			fieldname: "qty",
			label: __("For Quantity"),
			reqd: true
		}];

		const dialog = frappe.prompt(fields, function(data) {
			if (data.qty > qty) {
				frappe.throw(__("For Quantity must be less than quantity {0}", [qty]));
			}

			if (data.qty <= 0) {
				frappe.throw(__("For Quantity must be greater than zero"));
			}

			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.make_job_card",
				args: {
					work_order: frm.doc.name,
					operation: data.operation,
					workstation: data.workstation,
					qty: data.qty
				},
				callback: function(r){
					if (r.message) {
						var doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				}
			});
		}, __("For Job Card"));
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

	show_progress: function(frm) {
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
				var title = __('{0} items in progress', [pending_complete]);
				var width = ((pending_complete / frm.doc.qty * 100) - added_min);
				bars.push({
					'title': title,
					'width': (width > 100 ? "99.5" : width)  + '%',
					'progress_class': 'progress-bar-warning'
				})
				message = message + '. ' + title;
			}
		}
		frm.dashboard.add_progress(__('Status'), bars, message);
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
// 						frm.set_value('sales_order', "");
// 						frm.trigger('set_sales_order');
						erpnext.in_production_item_onchange = true;
						$.each(["description", "stock_uom", "project", "bom_no",
							"allow_alternative_item", "transfer_material_against"], function(i, field) {
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
		if(!erpnext.in_production_item_onchange) {
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
		frm.toggle_reqd(["fg_warehouse", "wip_warehouse"], true);
		frm.fields_dict.required_items.grid.toggle_reqd("source_warehouse", true);
		frm.toggle_reqd("transfer_material_against", frm.doc.operations);
		frm.fields_dict.operations.grid.toggle_reqd("workstation", frm.doc.operations);
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
						}
					});
				}
			});
		}
	}
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
			})
		}
	}
})

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
			})
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
		if (doc.docstatus === 1) {
			if (doc.status != 'Stopped' && doc.status != 'Completed') {
				frm.add_custom_button(__('Stop'), function() {
					erpnext.work_order.stop_work_order(frm, "Stopped");
				}, __("Status"));
			} else if (doc.status == 'Stopped') {
				frm.add_custom_button(__('Re-open'), function() {
					erpnext.work_order.stop_work_order(frm, "Resumed");
				}, __("Status"));
			}

			const show_start_btn = (frm.doc.skip_transfer
				|| frm.doc.transfer_material_against == 'Job Card') ? 0 : 1;

			if (show_start_btn){
				if ((flt(doc.material_transferred_for_manufacturing) < flt(doc.qty))
					&& frm.doc.status != 'Stopped') {
					frm.has_start_btn = true;
					var start_btn = frm.add_custom_button(__('Start'), function() {
						erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
					});
					start_btn.addClass('btn-primary');
				}
			}

			if(!frm.doc.skip_transfer){
				// If "Material Consumption is check in Manufacturing Settings, allow Material Consumption
				if ((flt(doc.produced_qty) < flt(doc.material_transferred_for_manufacturing))
				&& frm.doc.status != 'Stopped') {
					frm.has_finish_btn = true;

					if (frm.doc.__onload && frm.doc.__onload.material_consumption == 1) {
						// Only show "Material Consumption" when required_qty > consumed_qty
						var counter = 0;
						var tbl = frm.doc.required_items || [];
						var tbl_lenght = tbl.length;
						for (var i = 0, len = tbl_lenght; i < len; i++) {
							if (flt(frm.doc.required_items[i].required_qty) > flt(frm.doc.required_items[i].consumed_qty)) {
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

					var finish_btn = frm.add_custom_button(__('Finish'), function() {
						erpnext.work_order.make_se(frm, 'Manufacture');
					});

					if(doc.material_transferred_for_manufacturing>=doc.qty) {
						// all materials transferred for manufacturing, make this primary
						finish_btn.addClass('btn-primary');
					}
				}
			} else {
				if ((flt(doc.produced_qty) < flt(doc.qty)) && frm.doc.status != 'Stopped') {
					var finish_btn = frm.add_custom_button(__('Finish'), function() {
						erpnext.work_order.make_se(frm, 'Manufacture');
					});
					finish_btn.addClass('btn-primary');
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
		var variable_cost = frm.doc.actual_operating_cost ?
			flt(frm.doc.actual_operating_cost) : flt(frm.doc.planned_operating_cost)
		frm.set_value("total_operating_cost", (flt(frm.doc.additional_operating_cost) + variable_cost))
	},

	set_default_warehouse: function(frm) {
		if (!(frm.doc.wip_warehouse || frm.doc.fg_warehouse)) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_default_warehouse",
				callback: function(r) {
					if(!r.exe) {
						frm.set_value("wip_warehouse", r.message.wip_warehouse);
						frm.set_value("fg_warehouse", r.message.fg_warehouse)
					}
				}
			});
		}
	},

	make_se: function(frm, purpose) {
		if(!frm.doc.skip_transfer){
			var max = (purpose === "Manufacture") ?
				flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty) :
				flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
		} else {
			var max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
		}

		max = flt(max, precision("qty"));
		frappe.prompt({fieldtype:"Float", label: __("Qty for {0}", [purpose]), fieldname:"qty",
			description: __("Max: {0}", [max]), 'default': max }, function(data)
		{
			if(data.qty > max) {
				frappe.msgprint(__("Quantity must not be more than {0}", [max]));
				return;
			}
			frappe.call({
				method:"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
				args: {
					"work_order_id": frm.doc.name,
					"purpose": purpose,
					"qty": data.qty
				},
				callback: function(r) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			});
		}, __("Select Quantity"), __('Create'));
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

	stop_work_order: function(frm, status) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.work_order.work_order.stop_unstop",
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
		})
	}
}
