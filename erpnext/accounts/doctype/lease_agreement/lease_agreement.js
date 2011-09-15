$.extend(cur_frm.cscript, {
	Generate: function(doc, dt, dn) {
		if(doc.installment_amount==''){
			msgprint('Set Installment Amount before generating schedule');
			return;
		}
		if(doc.no_of_installments==''){
			msgprint('Set Number of Installments before generating schedule');
			return;
		}
		if(doc.start_date==''){
			msgprint('Set Start Date before generating schedule');
			return;
		}
		cur_frm.cscript.clear_installments(doc);
		tot=0;i=0;
		while(tot<flt(doc.invoice_amount)-flt(doc.down_payment)){
				d = LocalDB.add_child(doc, 'Lease Installment', 'installments');
				d.amount = flt(doc.installment_amount) < flt(doc.invoice_amount)-flt(doc.down_payment)-tot ? flt(doc.installment_amount) : flt(doc.invoice_amount)-flt(doc.down_payment)-tot
				d.due_date = dateutil.add_months(doc.start_date, i+1);
				tot += flt(doc.installment_amount)
				i++;
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
			show_field('Installment Reciept');hide_field('Generate');
		}
	},
	clear_installments: function(doc) {
		$.each(getchildren('Lease Installment', doc.name, 'installments', 'Lease Agreement'),
			function(i, d) {
				LocalDB.delete_doc('Lease Installment', d.name);
			}
		)
	},
	no_of_installments: function(doc)
	{
		if(flt(doc.no_of_installments)!=0) {
			doc.installment_amount = (flt(doc.invoice_amount)- flt(doc.down_payment))/flt(doc.no_of_installments);
			refresh_field('installment_amount');
		}
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
				$c_obj(make_doclist(dt,dn),'lease_installment_post',data,function(){cur_frm.refresh(); d.hide();});
			}
		}
	}
})


cur_frm.add_fetch('invoice','grand_total','invoice_amount');

cur_frm.fields_dict.invoice.get_query=function(doc){

	return "SELECT tv.name FROM `tabReceivable Voucher` tv WHERE debit_to='"+doc.account+"' and  tv.%(key)s like '%s' ORDER BY tv.name LIMIT 50"
}