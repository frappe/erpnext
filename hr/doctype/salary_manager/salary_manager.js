// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

var display_activity_log = function(msg) {
	if(!pscript.ss_html)
		pscript.ss_html = $a(cur_frm.fields_dict['activity_log'].wrapper,'div');
	pscript.ss_html.innerHTML = 
		'<div class="panel"><div class="panel-heading">'+wn._("Activity Log:")+'</div>'+msg+'</div>';
}

//Create salary slip
//-----------------------
cur_frm.cscript.create_salary_slip = function(doc, cdt, cdn) {
	var callback = function(r, rt){
		if (r.message)
			display_activity_log(r.message);
	}
	return $c('runserverobj', args={'method':'create_sal_slip','docs':wn.model.compress(make_doclist (cdt, cdn))},callback);
}



//Submit salary slip
//-----------------------
cur_frm.cscript.submit_salary_slip = function(doc, cdt, cdn) {
	var check = confirm(wn._("Do you really want to Submit all Salary Slip for month : ") + doc.month+ wn._(" and fiscal year : ")+doc.fiscal_year);
	if(check){
		var callback = function(r, rt){
			if (r.message)
				display_activity_log(r.message);
		}
		return $c('runserverobj', args={'method':'submit_salary_slip','docs':wn.model.compress(make_doclist (cdt, cdn))},callback);
	}
}

// Make Bank Voucher
//-----------------------
cur_frm.cscript.make_bank_voucher = function(doc,cdt,cdn){
  if(doc.month && doc.fiscal_year){
  	cur_frm.cscript.make_jv(doc, cdt, cdn);
  }
}


// Make JV
//-----------------------
cur_frm.cscript.make_jv = function(doc, dt, dn) {
	var call_back = function(r,rt){
		var jv = wn.model.make_new_doc_and_get_name('Journal Voucher');
		jv = locals['Journal Voucher'][jv];
		jv.voucher_type = 'Bank Voucher';
		jv.user_remark = wn._('Payment of salary for the month: ') + doc.month + wn._('and fiscal year: ') + doc.fiscal_year;
		jv.fiscal_year = doc.fiscal_year;
		jv.company = doc.company;
		jv.posting_date = dateutil.obj_to_str(new Date());

		// credit to bank
		var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
		d1.account = r.message['default_bank_account'];
		d1.credit = r.message['amount']

		// debit to salary account
		var d2 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
		d2.account = r.message['default_salary_account'];
		d2.debit = r.message['amount']

		loaddoc('Journal Voucher', jv.name);
	}
	return $c_obj(make_doclist(dt,dn),'get_acc_details','',call_back);
}
