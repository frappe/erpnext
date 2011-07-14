$.extend(cur_frm.cscript, {
	Generate: function(doc, dt, dn) {
		cur_frm.cscript.clear_installments(doc);
		for(var i=0; i< doc.no_of_installments; i++) {
			d = LocalDB.add_child(doc, 'Loan Installment', 'installments');
			d.amount = doc.loan_amount / doc.no_of_installments;
			d.due_date = dateutil.add_months(doc.start_date, i+1);
		}
		cur_frm.refresh();
	},
	clear_installments: function(doc) {
		$.each(getchildren('Loan Installment', doc.name, 'installments', 'Loan'), 
			function(i, d) {
				LocalDB.delete_doc('Loan Installment', d.name);
			}
		)
	}
})