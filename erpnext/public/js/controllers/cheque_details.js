frappe.ui.form.on(cur_frm.doctype, "onload", function(frm){
	cur_frm.set_query("cheque_lot", function(){
		return {
			"filters": [
				["status", "!=", "Used"],
				["docstatus", "=", "1"]
			]
		}
	});
});


frappe.ui.form.on(cur_frm.doctype, {
	cheque_lot: function(frm){
		if(frm.doc.cheque_lot) {
			frappe.call({
				method: "erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
				args: {
					'name': frm.doc.cheque_lot
				},
				callback: function(r){
					if (r.message) {
						if(cur_frm.doctype == 'Payment Entry'){
							cur_frm.set_value("reference_no", r.message[0].reference_no);
							cur_frm.set_value("reference_date", r.message[1].reference_no);
						} else {
							cur_frm.set_value("cheque_no", r.message[0].reference_no);
							cur_frm.set_value("cheque_date", r.message[1].reference_no);	
						}
					}
				}
			});
		}
	}
});
