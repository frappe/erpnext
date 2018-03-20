// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipping Plan', {
	setup: function(frm) {
		frm.set_query('delivery_note', function(){
			return{
				filters: {
					'docstatus': 0
				}
			};
		});

		frm.set_query('company_address_name', function(){
			return {
				filters: {
					"is_your_company_address": 1
				}
			};
		});

		frm.set_query('weight_uom', 'items', function() {
			return {
				filters:{
					"name": ["in", ["LB", "Kg"]]
				}
			}
		});
	},
	refresh: function(frm) {
		if(frm.doc.docstatus == 1){
			if(!frm.doc.is_pickup_scheduled && !frm.doc.__islocal){
				frm.add_custom_button(__('Schedule Pickup'),
					function() { cur_frm.cscript.schedule_pickup(); });
			}
		}
	},
	company_address_name: function(frm) {
		erpnext.utils.get_address_display(frm, 'company_address_name', 'company_address', true);
	},
	shipping_address_name: function(frm) {
		erpnext.utils.get_address_display(frm, 'shipping_address_name', 'shipping_address', true);
	},
	set_total_handling_units: function(frm) {
		var total_qty = 0;
		$.each(frm.doc.items || [], function(idx, row) {
			total_qty += row.qty;
		});
		frm.set_value("total_handling_unit", total_qty);
	}
});

frappe.ui.form.on('Shipping Plan Item', {
	qty: function(frm, cdt, cdn) {
		frm.trigger("set_total_handling_units");
	},
	items_remove: function(frm, cdt, cdn) {
		frm.trigger("set_total_handling_units");
	}
})

cur_frm.cscript.schedule_pickup = function(){
	var args = {
		"request_data": {
			"fedex_account":cur_frm.doc.shipper, "gross_weight":cur_frm.doc.gross_weight_pkg,
			"uom":cur_frm.doc.gross_weight_uom, "package_count":cur_frm.doc.no_of_packages,
			"shipper_id":cur_frm.doc.company_address_name, "email_id":"",
			"delivery_note":cur_frm.doc.delivery_note
			}
		}
	frappe.prompt(
		[
			{fieldtype:'Datetime', fieldname:'ready_time', label: __('Package Ready Time'), 'reqd':1},
		],
		function(data){
			args["request_data"]["ready_time"] = data.ready_time
			frappe.call({
				freeze:true,
				freeze_message: __("Scheduling pickup................."),
				method:"erpnext.logistics.doctype.shipping_plan.shipping_plan.schedule_pickup",
				args: args,
				callback:function(r){
				if(r.message.response == "SUCCESS"){
						cur_frm.set_value("is_pickup_scheduled", true);
						cur_frm.set_value("pickup_no", r.message.pickup_id);
						cur_frm.set_value("pickup_location", r.message.location_no);
						cur_frm.save_or_update();
						frappe.msgprint(__("Pickup service scheduled successfully."));
					}
				}
			})
		},__("Schedule pickup ?"), __("Yes"));
}