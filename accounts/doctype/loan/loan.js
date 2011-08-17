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
/*	submit:function(doc){
		data=doc.get_values();

		data['']=
		$c_obj(make_doclist(dt,dn),'loan_post',data,function(){});
	},*/
	refresh: function(doc) {
		cur_frm.cscript.hide_show_buttons(doc);
	},
	hide_show_buttons: function(doc) {
		if(doc.docstatus==0) {
			hide_field('Installment Reciept'); unhide_field('Generate');
		} else if (doc.docstatus==1) {
			unhide_field('Installment Reciept');hide_field('Generate');
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
				{fieldtype:'Data', label:'Cheque Number', fieldname:'cheque_number', reqd:1},
				{fieldtype:'Date', label:'Cheque Date', fieldname:'cheque_date', reqd:1},
				{fieldtype:'Link', label:'Bank Account', fieldname:'bank_account', reqd:1, options:'Account'},
				{fieldtype:'Button', label:'Update',fieldname:'update'}
			]
		})
		d.show();
		d.fields_dict.update.input.onclick = function() {
			var data = d.get_values();

			if(data) {
				$c_obj(make_doclist(dt,dn),'loan_installment_post',data,function(){cur_frm.refresh(); d.hide();});
			}
		}
	}
})
