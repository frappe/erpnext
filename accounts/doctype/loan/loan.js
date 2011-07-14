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
	refresh: function(doc) {
		cur_frm.cscript.hide_show_buttons(doc);
	},
	hide_show_buttons: function(doc) {
		if(doc.docstatus==0) {
			hide_field('Installment Reciept'); show_field('Generate');
		} else if (doc.docstatus==1) {
			show_field('Installment Reciept'); hide_field('Generate');			
		}
	},
	clear_installments: function(doc) {
		$.each(getchildren('Loan Installment', doc.name, 'installments', 'Loan'), 
			function(i, d) {
				LocalDB.delete_doc('Loan Installment', d.name);
			}
		)
	},
	'Installment Reciept': function(doc, dt, dn) {
		var d = new wn.widgets.Dialog({
			width: 500,
			title: 'Add a new payment installment',
			fields: [
				{fieldtype:'Data', label:'Check Number', fieldname:'check_number', reqd:1},
				{fieldtype:'Date', label:'Check Date', fieldname:'check_date', reqd:1},
				{fieldtype:'Button', label:'Update',fieldname:'update'}
			]
		})
		d.show();
		d.fields_dict.update.input.onclick = function() {
			var data = d.get_values();
			if(data) {
				$c_obj()
			}
		}
	}
})