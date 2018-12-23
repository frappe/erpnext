// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ready(function(){

	var loyalty_points_input = document.getElementById("loyalty-point-to-redeem");
	var loyalty_points_status = document.getElementById("loyalty-points-status");
	loyalty_points_input.onblur = apply_loyalty_points;

	function apply_loyalty_points() {
		var loyalty_points = parseInt(loyalty_points_input.value);
		if (loyalty_points) {
			frappe.call({
				method: "erpnext.accounting.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
				args: {
					"customer": doc_info.customer
				},
				callback: function(r) {
					if (r) {
						var message = ""
						let loyalty_amount = flt(r.message*loyalty_points);
						if (doc_info.grand_total && doc_info.grand_total < loyalty_amount) {
							let redeemable_amount = parseInt(doc_info.grand_total/r.message);
							message = "You can only redeem max " + redeemable_amount + " points in this order.";
							frappe.msgprint(__(message));
						} else {
							message = loyalty_points + " Loyalty Points of amount "+ loyalty_amount + " is applied."
							frappe.msgprint(__(message));
							var remaining_amount = flt(doc_info.grand_total) - flt(loyalty_amount);
							var payment_button = document.getElementById("pay-for-order");
							payment_button.innerHTML = __("Pay Remaining");
							payment_button.href = "/api/method/erpnext.accounting.doctype.payment_request.payment_request.make_payment_request?dn="+doc_info.doctype_name+"&dt="+doc_info.doctype+"&loyalty_points="+loyalty_points+"&submit_doc=1&order_type=Shopping Cart";
						}
						loyalty_points_status.innerHTML = message;
					}
				}
			});
		}
	}
})