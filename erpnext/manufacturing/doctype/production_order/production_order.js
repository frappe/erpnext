// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function (doc, dt, dn) {

		if (!doc.status) doc.status = 'Draft';
		cfn_set_fields(doc, dt, dn);

		this.frm.add_fetch("sales_order", "delivery_date", "expected_delivery_date");
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
		return this.frm.call({
			method: "get_item_details",
			args: { item: doc.production_item }
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
	cur_frm.cscript.make_se('Material Transfer');
}

cur_frm.cscript['Update Finished Goods'] = function() {
	cur_frm.cscript.make_se('Manufacture/Repack');
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
