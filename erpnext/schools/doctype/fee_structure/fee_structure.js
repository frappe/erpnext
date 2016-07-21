frappe.ui.form.on("Fee Amount", {
	amount: function(frm) {
		total_amount = 0;
		for(var i=0;i<frm.doc.amount.length;i++) {
			total_amount += frm.doc.amount[i].amount;
		}
		frm.set_value("total_amount", total_amount);
	}
});