var display_activity_log = function(msg) {
	if(!pscript.ss_html)
		pscript.ss_html = $a(cur_frm.fields_dict['Activity Log'].wrapper,'div','',{border:'1px solid #CCC', backgroundColor:'#CCC'});
	pscript.ss_html.innerHTML = '<div style="color:#EEE; background-color:#555;"><b><i>Activity Log:</i><br></b></div>';
	pscript.ss_html.innerHTML += '<div style="color:#666; padding: 5px">'+ msg + '</div>';
}

//Create salary slip
//-----------------------
cur_frm.cscript['Create Salary Slip'] = function(doc, cdt, cdn) {
	var callback = function(r, rt){
		if (r.message)
			display_activity_log(r.message);
	}
	$c('runserverobj', args={'method':'create_sal_slip','docs':compress_doclist(make_doclist (cdt, cdn))},callback);
}



//Submit salary slip
//-----------------------
cur_frm.cscript['Submit Salary Slip'] = function(doc, cdt, cdn) {
	var check = confirm("Do you really want to Submit all Salary Slip for month : " + doc.month+" and fiscal year : "+doc.fiscal_year);
	if(check){
		var callback = function(r, rt){
			if (r.message)
				display_activity_log(r.message);
		}
		$c('runserverobj', args={'method':'submit_salary_slip','docs':compress_doclist(make_doclist (cdt, cdn))},callback);
	}
}

// Make Bank Voucher
//-----------------------
cur_frm.cscript['Make Bank Voucher'] = function(doc,cdt,cdn){
  if(doc.month && doc.fiscal_year){
  	cur_frm.cscript.make_jv(doc, cdt, cdn);
  }
}


// Make JV
//-----------------------
cur_frm.cscript.make_jv = function(doc, dt, dn) {
	var call_back = function(r,rt){
		var jv = LocalDB.create('Journal Voucher');
		jv = locals['Journal Voucher'][jv];
		jv.voucher_type = 'Bank Voucher';
		jv.user_remark = 'Payment of salary for the month: ' + doc.month + 'and fiscal year: ' + doc.fiscal_year;
		jv.fiscal_year = doc.fiscal_year;
		jv.company = doc.company;
		jv.posting_date = dateutil.obj_to_str(new Date());

		// credit to bank
		var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
		d1.account = r.message['default_bank_account'];
		d1.credit = r.message['amount']

		// debit to salary account
		var d2 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
		d2.account = r.message['default_salary_account'];
		d2.debit = r.message['amount']

		loaddoc('Journal Voucher', jv.name);
	}
	$c_obj(make_doclist(dt,dn),'get_acc_details','',call_back);
}
