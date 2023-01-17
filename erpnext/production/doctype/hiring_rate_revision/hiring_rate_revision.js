// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hiring Rate Revision', {
	refresh: function(frm) {

	},
	setup:function(frm){
		frm.set_query("item_code",function(){
			return {
				filters:{disabled:0,
				is_pol_item:1}
			}
		})
	},
	valid_from:function(frm){
		get_current_fuel_price(frm)
		fetch_previous_price(frm)
	},
	fuel_price_list:function(frm){
		get_current_fuel_price(frm)
		fetch_previous_price(frm)
	},
	item_code:function(frm){
		fetch_previous_price(frm)
		get_current_fuel_price(frm)
	},
	branch:function(frm){
		cur_frm.set_query("fuel_price_list", function() {
            return {
                query: "erpnext.production.doctype.hiring_rate_revision.hiring_rate_revision.filter_fuel_price_list",
                filters: {'branch': frm.doc.branch}
            }
        });
	},
	get_equipment:function(frm){
		get_hired_equipment(frm)
	}
});

// var calculate_variance = function(frm){
// 	if ( flt(frm.doc.previous_price) > 0 && flt(frm.doc.current_price) > 0){
// 		frm.doc.variance = flt((flt(frm.doc.current_price) - (frm.doc.previous_price))/flt(frm.doc.current_price)) * 100
// 	}
// }

var get_hired_equipment = function(frm){
	frappe.call({
		method:"get_hired_equipment",
		doc:frm.doc,
		callback: function (r) {
			frm.refresh_fields();
			frm.dirty()
	},
	freeze: true,
	freeze_message: "Fetching Data....."
	})
}
var fetch_previous_price = function(frm){
	if (frm.doc.valid_from && frm.doc.fuel_price_list && frm.doc.item_code){
		frappe.call({
			method:"get_previous_rate",
			doc : frm.doc,
			callback:function(r){
				frm.refresh_field("previous_price")
			}
		})
	}
}
var get_current_fuel_price = function(frm){
	if (frm.doc.valid_from && frm.doc.fuel_price_list && frm.doc.item_code){
		frappe.call({
			method:"erpnext.production.doctype.fuel_price.fuel_price.get_current_fuel_price",
			args:{
				"item_code":frm.doc.item_code,
				"valid_from":frm.doc.valid_from,
				"fuel_price_list":frm.doc.fuel_price_list,
				"uom":frm.doc.uom
			},
			callback:function(r){
				if ( r.message.length > 0){
					frm.set_value("current_price",r.message[0].rate)
					frm.refresh_field("current_price")
				}else{
					frm.set_value("current_price",0)
					frm.refresh_field("current_price")
				}
			}
		})
	}
}
