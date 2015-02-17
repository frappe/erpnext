// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function (doc, dt, dn) {
		if (!doc.status) doc.status = 'Draft';
		cfn_set_fields(doc, dt, dn);

		this.frm.add_fetch("sales_order", "delivery_date", "expected_delivery_date");

		if(doc.__islocal) {
			cur_frm.set_value({
			"actual_start_date": "",
			"actual_end_date": ""
			});
		}
	},

	before_submit: function() {
		cur_frm.toggle_reqd(["fg_warehouse", "wip_warehouse"], true);
	},

	refresh: function(doc, dt, dn) {
		this.frm.dashboard.reset();
		erpnext.toggle_naming_series();
		this.frm.set_intro("");
		cfn_set_fields(doc, dt, dn);

		if (doc.docstatus === 0 && !doc.__islocal) {
			this.frm.set_intro(__("Submit this Production Order for further processing."));
		} else if (doc.docstatus === 1) {
			var percent = flt(doc.produced_qty) / flt(doc.qty) * 100;
			this.frm.dashboard.add_progress(cint(percent) + "% " + __("Complete"), percent);

			if(doc.status === "Stopped") {
				this.frm.dashboard.set_headline_alert(__("Stopped"), "alert-danger", "icon-stop");
			}
		}
	},

	production_item: function(doc) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_order.production_order.get_item_details",
			args: { item: doc.production_item },
			callback: function(r) {
				cur_frm.set_value(r.message);
			}
		});
	},

	make_se: function(purpose) {
		var me = this;

		frappe.call({
			method:"erpnext.manufacturing.doctype.production_order.production_order.make_stock_entry",
			args: {
				"production_order_id": me.frm.doc.name,
				"purpose": purpose
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	bom_no: function() {
		return this.frm.call({
			doc: this.frm.doc,
			method: "set_production_order_operations"
		});
	},

	planned_start_date: function() {
		return this.frm.call({
			doc: this.frm.doc,
			method: "plan_operations"
		});
	},

	make_time_log: function(doc, cdt, cdn){
		var child = locals[cdt][cdn]
		frappe.call({
			method:"erpnext.manufacturing.doctype.production_order.production_order.make_time_log",
			args: {
				"name": doc.name,
				"operation": child.idx + ". " + child.operation,
				"from_time": child.planned_start_time,
				"to_time": child.planned_end_time,
				"project": doc.project,
				"workstation": child.workstation,
				"qty": flt(doc.qty) - flt(child.completed_qty)
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	auto_time_log: function(doc){
		frappe.call({
			method:"erpnext.manufacturing.doctype.production_order.production_order.auto_make_time_log",
			args: {
				"production_order_id": doc.name
			}
		});
	}
});

var cfn_set_fields = function(doc, dt, dn) {
	if (doc.docstatus == 1) {

		if (doc.status == 'Submitted' || doc.status == 'Material Transferred' || doc.status == 'In Process'){
			cur_frm.add_custom_button(__('Transfer Raw Materials'),
				cur_frm.cscript['Transfer Raw Materials'], frappe.boot.doctype_icons["Stock Entry"]);
			cur_frm.add_custom_button(__('Update Finished Goods'),
				cur_frm.cscript['Update Finished Goods'], frappe.boot.doctype_icons["Stock Entry"]);
		}

		if (doc.status != 'Stopped' && doc.status != 'Completed') {
			cur_frm.add_custom_button(__('Stop'), cur_frm.cscript['Stop Production Order'],
				"icon-exclamation", "btn-default");
		} else if (doc.status == 'Stopped') {
			cur_frm.add_custom_button(__('Unstop'), cur_frm.cscript['Unstop Production Order'],
			"icon-check", "btn-default");
		}
	}
}

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
			['Item', 'is_pro_applicable', '=', 'Yes']
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

cur_frm.set_query("bom_no", function(doc) {
	if (doc.production_item) {
		return{
			query: "erpnext.controllers.queries.bom",
			filters: {item: cstr(doc.production_item)}
		}
	} else msgprint(__("Please enter Production Item first"));
});


var calculate_total_cost = function(frm) {
	var variable_cost = frm.doc.actual_operating_cost ? flt(frm.doc.actual_operating_cost) : flt(frm.doc.planned_operating_cost)
	frm.set_value("total_operating_cost", (flt(frm.doc.additional_operating_cost) + variable_cost))
}

frappe.ui.form.on("Production Order", "additional_operating_cost", function(frm) {
	calculate_total_cost(frm);
});

frappe.ui.form.on("Production Order Operation", "workstation", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	frappe.call({
		"method": "frappe.client.get",
		args: {
			doctype: "Workstation",
			name: d.workstation
		},
		callback: function (data) {
			frappe.model.set_value(d.doctype, d.name, "hour_rate", data.message.hour_rate);
			calculate_cost(frm.doc);
			calculate_total_cost(frm);
		}
	})
});

var calculate_cost = function(doc) {
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
}

frappe.ui.form.on("Production Order Operation", "time_in_mins", function(frm, cdt, cdn) {
	calculate_cost(frm.doc);
	calculate_total_cost(frm)
});