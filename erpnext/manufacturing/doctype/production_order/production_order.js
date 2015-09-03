// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Production Order", "onload", function(frm) {
	if (!frm.doc.status)
		frm.doc.status = 'Draft';

	frm.add_fetch("sales_order", "delivery_date", "expected_delivery_date");

	if(frm.doc.__islocal) {
		frm.set_value({
			"actual_start_date": "",
			"actual_end_date": ""
		});
		erpnext.production_order.set_default_warehouse(frm);
	}

	erpnext.production_order.set_custom_buttons(frm);
	erpnext.production_order.setup_company_filter(frm);
	erpnext.production_order.setup_bom_filter(frm);
});

frappe.ui.form.on("Production Order", "refresh", function(frm) {
	erpnext.toggle_naming_series();
	frm.set_intro("");
	erpnext.production_order.set_custom_buttons(frm);

	if (frm.doc.docstatus === 0 && !frm.doc.__islocal) {
		frm.set_intro(__("Submit this Production Order for further processing."));
	}
});

frappe.ui.form.on("Production Order", "additional_operating_cost", function(frm) {
	erpnext.production_order.calculate_total_cost(frm);
});

frappe.ui.form.on("Production Order Operation", "workstation", function(frm, cdt, cdn) {
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
});

frappe.ui.form.on("Production Order Operation", "time_in_mins", function(frm, cdt, cdn) {
	erpnext.production_order.calculate_cost(frm.doc);
	erpnext.production_order.calculate_total_cost(frm)
});

erpnext.production_order = {
	set_custom_buttons: function(frm) {
		var doc = frm.doc;
		if (doc.docstatus === 1) {

			if (flt(doc.material_transferred_for_manufacturing) < flt(doc.qty)) {
				frm.add_custom_button(__('Transfer Materials for Manufacture'),
					cur_frm.cscript['Transfer Raw Materials'], frappe.boot.doctype_icons["Stock Entry"]);
			}

			if (flt(doc.produced_qty) < flt(doc.material_transferred_for_manufacturing)) {
				frm.add_custom_button(__('Update Finished Goods'),
					cur_frm.cscript['Update Finished Goods'], frappe.boot.doctype_icons["Stock Entry"]);
			}

			frm.add_custom_button(__("Show Stock Entries"), function() {
				frappe.route_options = {
					production_order: frm.doc.name
				}
				frappe.set_route("List", "Stock Entry");
			});

			if (doc.status != 'Stopped' && doc.status != 'Completed') {
				frm.add_custom_button(__('Stop'), cur_frm.cscript['Stop Production Order'],
					"icon-exclamation", "btn-default");
			} else if (doc.status == 'Stopped') {
				frm.add_custom_button(__('Unstop'), cur_frm.cscript['Unstop Production Order'],
				"icon-check", "btn-default");
			}

			// opertions
			if ((doc.operations || []).length) {
				frm.add_custom_button(__('Show Time Logs'), function() {
					frappe.route_options = {"production_order": frm.doc.name};
					frappe.set_route("List", "Time Log");
				});
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
					'company': frm.doc.company
				}
			}
		}

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

$.extend(cur_frm.cscript, {
	before_submit: function() {
		cur_frm.toggle_reqd(["fg_warehouse", "wip_warehouse"], true);
	},

	production_item: function(doc) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_order.production_order.get_item_details",
			args: { item: doc.production_item },
			callback: function(r) {
				$.each(["description", "stock_uom", "bom_no"], function(i, field) {
					cur_frm.set_value(field, r.message[field]);
				});
			}
		});
	},

	make_se: function(purpose) {
		var me = this;
		var max = (purpose === "Manufacture") ?
			flt(this.frm.doc.material_transferred_for_manufacturing) - flt(this.frm.doc.produced_qty) :
			flt(this.frm.doc.qty) - flt(this.frm.doc.material_transferred_for_manufacturing);

		frappe.prompt({fieldtype:"Int", label: __("Qty for {0}", [purpose]), fieldname:"qty",
			description: __("Max: {0}", [max]) },
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
			method: "set_production_order_operations"
		});
	},

	qty: function() {
		frappe.ui.form.trigger("Production Order", 'bom_no')
	},
	show_time_logs: function(doc, cdt, cdn) {
		var child = locals[cdt][cdn]
		frappe.route_options = {"operation_id": child.name};
		frappe.set_route("List", "Time Log");
	},

	make_time_log: function(doc, cdt, cdn){
		var child = locals[cdt][cdn]
		frappe.call({
			method:"erpnext.manufacturing.doctype.production_order.production_order.make_time_log",
			args: {
				"name": doc.name,
				"operation": child.operation,
				"from_time": child.planned_start_time,
				"to_time": child.planned_end_time,
				"project": doc.project,
				"workstation": child.workstation,
				"qty": flt(doc.qty) - flt(child.completed_qty),
				"operation_id": child.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
});

cur_frm.cscript['Stop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(__("Do you really want to stop production order: " + doc.name));
	if (check) {
		return $c_obj(doc, 'stop_unstop', 'Stopped', function(r, rt) {cur_frm.refresh();});
	}
}

cur_frm.cscript['Unstop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(__("Do really want to unstop production order: " + doc.name));
	if (check)
		return $c_obj(doc, 'stop_unstop', 'Unstopped', function(r, rt) {cur_frm.refresh();});
}

cur_frm.cscript['Transfer Raw Materials'] = function() {
	cur_frm.cscript.make_se('Material Transfer for Manufacture');
}

cur_frm.cscript['Update Finished Goods'] = function() {
	cur_frm.cscript.make_se('Manufacture');
}

cur_frm.fields_dict['production_item'].get_query = function(doc) {
	return {
		filters:[
			['Item', 'is_pro_applicable', '=', 1],
			['Item', 'has_variants', '=', 0],
			['Item', 'end_of_life', '>=', frappe.datetime.nowdate()]
		]
	}
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}
