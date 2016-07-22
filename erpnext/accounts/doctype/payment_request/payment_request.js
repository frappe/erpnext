cur_frm.add_fetch("payment_gateway", "payment_account", "payment_account")
cur_frm.add_fetch("payment_gateway", "payment_gateway", "payment_gateway")
cur_frm.add_fetch("payment_gateway", "message", "message")
cur_frm.add_fetch("payment_gateway", "payment_url_message", "payment_url_message")

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
	if(!in_list(["Initiated", "Paid"], frm.doc.status) && !frm.doc.__islocal && frm.doc.docstatus==1){
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
	}
	
	if(!frm.doc.payment_gateway_account && frm.doc.status == "Initiated") {
		frm.add_custom_button(__('Make Payment Entry'), function(){
			frappe.call({
				method: "erpnext.accounts.doctype.payment_request.payment_request.make_payment_entry",
				args: {"docname": frm.doc.name},
				freeze: true,
				callback: function(r){
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			});
		}).addClass("btn-primary");
	}
});

