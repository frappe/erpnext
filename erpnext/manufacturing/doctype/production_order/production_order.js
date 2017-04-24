// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Production Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Timesheet': 'Make Timesheet',
			'Stock Entry': 'Make Stock Entry',
		}
	},
	onload: function(frm) {
		if (!frm.doc.status)
			frm.doc.status = 'Draft';

		frm.add_fetch("sales_order", "delivery_date", "expected_delivery_date");
		frm.add_fetch("sales_order", "project", "project");

		if(frm.doc.__islocal) {
			frm.set_value({
				"actual_start_date": "",
				"actual_end_date": ""
			});
			erpnext.production_order.set_default_warehouse(frm);
		}

		// formatter for production order operation
		frm.set_indicator_formatter('operation',
			function(doc) { return (frm.doc.qty==doc.completed_qty) ? "green" : "orange" })

		erpnext.production_order.set_custom_buttons(frm);
		erpnext.production_order.setup_company_filter(frm);
		erpnext.production_order.setup_bom_filter(frm);
	},
	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.production_order.set_custom_buttons(frm);
		frm.set_intro("");

		if (frm.doc.docstatus === 0 && !frm.doc.__islocal) {
			frm.set_intro(__("Submit this Production Order for further processing."));
		}

		if (frm.doc.docstatus===1) {
			frm.trigger('show_progress');
		}

		if(frm.doc.docstatus == 1 && frm.doc.status != 'Stopped'){
			frm.add_custom_button(__('Make Timesheet'), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.production_order.production_order.make_new_timesheet",
					frm: cur_frm
				})
			})
		}
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
		if(bars[0].width=='0%') {
			 bars[0].width = '0.5%';
			 added_min = 0.5;
		 }
		message = title;

		// pending qty
		if(!frm.doc.skip_transfer){
			var pending_complete = frm.doc.material_transferred_for_manufacturing - frm.doc.produced_qty;
			if(pending_complete) {
				var title = __('{0} items in progress', [pending_complete]);
				bars.push({
					'title': title,
					'width': ((pending_complete / frm.doc.qty * 100) - added_min)  + '%',
					'progress_class': 'progress-bar-warning'
				})
				message = message + '. ' + title;
			}
		}
		frm.dashboard.add_progress(__('Status'), bars, message);
	}
});



frappe.ui.form.on("Production Order Operation", {
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
					erpnext.production_order.calculate_cost(frm.doc);
					erpnext.production_order.calculate_total_cost(frm);
				}
			})
		}
	},
	time_in_mins: function(frm, cdt, cdn) {
		erpnext.production_order.calculate_cost(frm.doc);
		erpnext.production_order.calculate_total_cost(frm);
	},
});

erpnext.production_order = {
	set_custom_buttons: function(frm) {
		var doc = frm.doc;
		if (doc.docstatus === 1) {
			if (doc.status != 'Stopped' && doc.status != 'Completed') {
				frm.add_custom_button(__('Stop'), cur_frm.cscript['Stop Production Order'], __("Status"));
			} else if (doc.status == 'Stopped') {
				frm.add_custom_button(__('Re-open'), cur_frm.cscript['Unstop Production Order'], __("Status"));
			}

			if(!frm.doc.skip_transfer){
				if ((flt(doc.material_transferred_for_manufacturing) < flt(doc.qty)) && frm.doc.status != 'Stopped') {
				frm.has_start_btn = true;
				var btn = frm.add_custom_button(__('Start'),
					cur_frm.cscript['Transfer Raw Materials']);
				btn.addClass('btn-primary');
				}
			}

			if(!frm.doc.skip_transfer){
				if ((flt(doc.produced_qty) < flt(doc.material_transferred_for_manufacturing)) && frm.doc.status != 'Stopped') {
					frm.has_finish_btn = true;
					var btn = frm.add_custom_button(__('Finish'),
						cur_frm.cscript['Update Finished Goods']);

					if(doc.material_transferred_for_manufacturing==doc.qty) {
						// all materials transferred for manufacturing,
						// make this primary
						btn.addClass('btn-primary');
					}
				}
			} else {
				if ((flt(doc.produced_qty) < flt(doc.qty)) && frm.doc.status != 'Stopped') {
					frm.has_finish_btn = true;
					var btn = frm.add_custom_button(__('Finish'),
						cur_frm.cscript['Update Finished Goods']);
					btn.addClass('btn-primary');
				}
			}
		}

	},
	calculate_cost: function(doc) {
		if (doc.operations){
			var op = doc.operations;
			doc.planned_operating_cost = 0.0;
			for(var i=0;i<op.length;i++) {
				planned_operating_cost = flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
				frappe.model.set_value('Production Order Operation',op[i].name, "planned_operating_cost", planned_operating_cost);

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

	setup_company_filter: function(frm) {
		var company_filter = function(doc) {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			}
		}

		frm.fields_dict.source_warehouse.get_query = company_filter;
		frm.fields_dict.fg_warehouse.get_query = company_filter;
		frm.fields_dict.wip_warehouse.get_query = company_filter;
	},

	setup_bom_filter: function(frm) {
		frm.set_query("bom_no", function(doc) {
			if (doc.production_item) {
				return{
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(doc.production_item)}
				}
			} else msgprint(__("Please enter Production Item first"));
		});
	},

	set_default_warehouse: function(frm) {
		if (!(frm.doc.wip_warehouse || frm.doc.fg_warehouse)) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.production_order.production_order.get_default_warehouse",

				callback: function(r) {
					if(!r.exe) {
						frm.set_value("wip_warehouse", r.message.wip_warehouse);
						frm.set_value("fg_warehouse", r.message.fg_warehouse)
					}
				}
			});
		}
	}
}

$.extend(cur_frm.cscript, {
	before_submit: function() {
		cur_frm.toggle_reqd(["fg_warehouse", "wip_warehouse"], true);
	},

	production_item: function(doc) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_order.production_order.get_item_details",
			args: {
					item: doc.production_item,
					project: doc.project
					},
			callback: function(r) {
				$.each(["description", "stock_uom", "project", "bom_no"], function(i, field) {
					cur_frm.set_value(field, r.message[field]);
				});

				if(r.message["set_scrap_wh_mandatory"]){
					cur_frm.toggle_reqd("scrap_warehouse", true);
				}
			}
		});
	},

	project: function(doc) {
		cur_frm.cscript.production_item(doc)
	},

	make_se: function(purpose) {
		var me = this;
		if(!this.frm.doc.skip_transfer){
			var max = (purpose === "Manufacture") ?
				flt(this.frm.doc.material_transferred_for_manufacturing) - flt(this.frm.doc.produced_qty) :
				flt(this.frm.doc.qty) - flt(this.frm.doc.material_transferred_for_manufacturing);
		} else {
			var max = flt(this.frm.doc.qty) - flt(this.frm.doc.produced_qty);
		}

		frappe.prompt({fieldtype:"Float", label: __("Qty for {0}", [purpose]), fieldname:"qty",
			description: __("Max: {0}", [max]), 'default': max },
			function(data) {
				if(data.qty > max) {
					frappe.msgprint(__("Quantity must not be more than {0}", [max]));
					return;
				}
				frappe.call({
					method:"erpnext.manufacturing.doctype.production_order.production_order.make_stock_entry",
					args: {
						"production_order_id": me.frm.doc.name,
						"purpose": purpose,
						"qty": data.qty
					},
					callback: function(r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				});
			}, __("Select Quantity"), __("Make"));
	},

	bom_no: function() {
		return this.frm.call({
			doc: this.frm.doc,
			method: "set_production_order_operations",
			callback: function(r) {
				if(r.message["set_scrap_wh_mandatory"]){
					cur_frm.toggle_reqd("scrap_warehouse", true);
				}
			}
		});
	},
	
	use_multi_level_bom: function() {
		if(this.frm.doc.bom_no) {
			this.frm.trigger("bom_no");
		}
	},

	qty: function() {
		frappe.ui.form.trigger("Production Order", 'bom_no')
	},
});

cur_frm.cscript['Stop Production Order'] = function() {
	$c_obj(cur_frm.doc, 'stop_unstop', 'Stopped', function(r, rt) {cur_frm.refresh();});
}

cur_frm.cscript['Unstop Production Order'] = function() {
	$c_obj(cur_frm.doc, 'stop_unstop', 'Unstopped', function(r, rt) {cur_frm.refresh();});
}

cur_frm.cscript['Transfer Raw Materials'] = function() {
	cur_frm.cscript.make_se('Material Transfer for Manufacture');
}

cur_frm.cscript['Update Finished Goods'] = function() {
	cur_frm.cscript.make_se('Manufacture');
}

cur_frm.fields_dict['production_item'].get_query = function(doc) {
	return {
		query: "erpnext.controllers.queries.item_query",
		filters:{
			'is_stock_item': 1,
		}
	}
}

cur_frm.fields_dict['project'].get_query = function(doc, dt, dn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}