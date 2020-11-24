// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Insurance Claim', {
	refresh: function(frm) {
		frm.set_query('healthcare_insurance_coverage_plan', function(){
				return{
					filters:{
						'is_active': 1
					}
				};
		});
		frm.set_query('insurance_subscription', function(){
			return{
				filters:{
					'patient': frm.doc.patient,
					'docstatus': 1
				}
			};
		});
	},
	price_list_rate: function(frm) {
		if(frm.doc.price_list_rate){
			calculate_claim_amount_on_update(frm)
		}
	},
	discount: function (frm) {
		if(frm.doc.discount){
			calculate_claim_amount_on_update(frm)
		}
	},
	coverage:function (frm) {
		if(frm.doc.coverage){
			calculate_claim_amount_on_update(frm)
		}
	}
});
let calculate_claim_amount_on_update = function(frm){
	if(frm.doc.price_list_rate){
		var discount_amount = 0.0
		var rate = frm.doc.price_list_rate
		if(frm.doc.discount){
			discount_amount = flt(frm.doc.price_list_rate) * flt(frm.doc.discount) * 0.01;
			rate = flt(rate) - flt(discount_amount)
		}
		var amount = flt(frm.doc.quantity) * flt(rate);
		frm.set_value('amount', amount);
	}
	if(frm.doc.amount && frm.doc.coverage){
		var coverage_amount = flt(frm.doc.amount) * 0.01 * flt(frm.doc.coverage);
		frm.set_value('coverage_amount', coverage_amount);
	}
}
