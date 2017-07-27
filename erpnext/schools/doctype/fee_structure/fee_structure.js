frappe.ui.form.on("Fee Component", {
	amount: function(frm) {
		var total_amount = 0;
		for(var i=0;i<frm.doc.components.length;i++) {
			total_amount += frm.doc.components[i].amount;
		}
		frm.set_value("total_amount", total_amount);
	}
});