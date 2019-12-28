// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Coupon Code', {
	setup: function(frm) {
		frm.set_query("pricing_rule", function() {
			return {
				filters: [
					["Pricing Rule","coupon_code_based", "=", "1"]
				]
			};
		});
	},
	coupon_name:function(frm){
		if (frm.doc.__islocal===1) {
			frm.trigger("make_coupon_code");
		}
	},
	coupon_type:function(frm){
		if (frm.doc.__islocal===1) {
			frm.trigger("make_coupon_code");
		}
	},
	make_coupon_code: function(frm) {
		var coupon_name=frm.doc.coupon_name;
		var coupon_code;
		if (frm.doc.coupon_type=='Gift Card') {
			coupon_code=Math.random().toString(12).substring(2, 12).toUpperCase();
		}
		else if(frm.doc.coupon_type=='Promotional'){
			coupon_name=coupon_name.replace(/\s/g,'');
			coupon_code=coupon_name.toUpperCase().slice(0,8);
		}
		frm.doc.coupon_code=coupon_code;
		frm.refresh_field('coupon_code');
	},
	refresh: function(frm) {
		if (frm.doc.pricing_rule) {
			frm.add_custom_button(__("Add/Edit Coupon Conditions"), function(){
				frappe.set_route("Form", "Pricing Rule", frm.doc.pricing_rule);
			});
		}
	}
});
