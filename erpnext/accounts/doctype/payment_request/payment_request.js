cur_frm.add_fetch("payment_gateway", "payment_account", "payment_account")
cur_frm.add_fetch("payment_gateway", "gateway", "gateway")
cur_frm.add_fetch("payment_gateway", "message", "message")

frappe.ui.form.on("Payment Request", "onload", function(frm, dt, dn){
	frappe.call({
		method:"erpnext.accounts.doctype.payment_request.payment_request.get_print_format_list",
		args: {"ref_doctype": frm.doc.reference_doctype},
		callback:function(r){
			set_field_options("print_format", r.message["print_format"])
		}
	})
})