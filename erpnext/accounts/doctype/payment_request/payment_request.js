cur_frm.add_fetch("payment_gateway", "payment_account", "payment_account")
cur_frm.add_fetch("payment_gateway", "gateway", "gateway")
cur_frm.add_fetch("payment_gateway", "message", "message")
cur_frm.add_fetch("payment_gateway", "payment_url_message", "payment_url_message")
cur_frm.add_fetch("payment_gateway", "payment_success_url", "payment_success_url")

frappe.ui.form.on("Payment Request", "onload", function(frm, dt, dn){
	if (frm.doc.reference_doctype) {
		frappe.call({
			method:"erpnext.accounts.doctype.payment_request.payment_request.get_print_format_list",
			args: {"ref_doctype": frm.doc.reference_doctype},
			callback:function(r){
				set_field_options("print_format", r.message["print_format"])
			}
		})
	}
})

frappe.ui.form.on("Payment Request", "refresh", function(frm) {
	frm.add_custom_button(__('Resend Payment Email'), function(){
		frappe.call({
			method: "erpnext.accounts.doctype.payment_request.payment_request.resend_payment_email",
			args: {"docname": frm.doc.name},
			freeze: true,
			freeze_message: __("Sending"),
			callback: function(r){
				if(!r.exc) {
					frappe.msgprint(__("Message Sent"));
				}
			}
		});
	});
});

