

frappe.ready(function(){

	var loyalty_apply_button = document.getElementById("loyalty-apply-button");
	var loyalty_points_input = document.getElementById("loyalty-point-to-redeem");
	loyalty_apply_button.addEventListener("click", apply_loyalty_points);

	
	function apply_loyalty_points() {
		frappe.call({
			method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
			args: {
				"customer": doc_info.customer
			},
			callback: function(r) {
				if (r) {
					// debugger;
					var loyalty_points = loyalty_points_input.value;
					let loyalty_amount = flt(r.message*loyalty_points);
					if (doc_info.grand_total && doc_info.grand_total < loyalty_amount) {
						let redeemable_amount = parseInt(doc_info.grand_total/r.message);
						frappe.msgprint(__("You can only redeem max " + redeemable_amount + " points in this order."));
					} else {
						frappe.msgprint(__("Loyalty Points of amount "+ loyalty_amount + " is applied."));
						var remaining_amount = flt(doc_info.grand_total) - flt(loyalty_amount);
						console.log(remaining_amount);
						var payment_button = document.getElementById("pay-for-order");
						payment_button.innerHTML = payment_button.innerHTML.split(doc_info.grand_total)[0] + remaining_amount;
						payment_button.href = "/api/method/erpnext.accounts.doctype.payment_request.payment_request.make_payment_request?dn="+doc_info.doctype_name+"&dt="+doc_info.doctype+"&loyalty_points="+loyalty_points+"&submit_doc=1&order_type=Shopping Cart";
						// var loyalty_points_input = document.getElementById("pay-for-order");


						// frm.events.apply_loyalty_points(frm);
					}
				}
			}
		});
	}
	// $("#loyalty-apply-button").on('click', function(){
	// 	let points_to_redeem = $("#loyalty-point-to-redeem").val():
	// 	if (points_to_redeem) {
	// 		alert(points_to_redeem);

	// 	}
	// })
})