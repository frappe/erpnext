// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

var display_activity_log = function(msg) {
	if(!pscript.ss_html)
		pscript.ss_html = $a(cur_frm.fields_dict['activity_log'].wrapper,'div','',{border:'1px solid #CCC', backgroundColor:'#CCC'});
	pscript.ss_html.innerHTML = '<div style="color:#EEE; background-color:#555;"><b><i>Activity Log:</i><br></b></div>';
	pscript.ss_html.innerHTML += '<div style="color:#666; padding: 5px">'+ msg + '</div>';
}

//Create salary slip
//-----------------------
cur_frm.cscript.create_salary_slip = function(doc, cdt, cdn) {
	var callback = function(r, rt){
		if (r.message)
			display_activity_log(r.message);
	}
	$c('runserverobj', args={'method':'create_sal_slip','docs':wn.model.compress(make_doclist (cdt, cdn))},callback);
}



//Submit salary slip
//-----------------------
cur_frm.cscript.submit_salary_slip = function(doc, cdt, cdn) {
	var check = confirm("Do you really want to Submit all Salary Slip for month : " + doc.month+" and fiscal year : "+doc.fiscal_year);
	if(check){
		var callback = function(r, rt){
			if (r.message)
				display_activity_log(r.message);
		}
		$c('runserverobj', args={'method':'submit_salary_slip','docs':wn.model.compress(make_doclist (cdt, cdn))},callback);
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
		jv.user_remark = 'Payment of salary for the month: ' + doc.month + 'and fiscal year: ' + doc.fiscal_year;
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
	$c_obj(make_doclist(dt,dn),'get_acc_details','',call_back);
}
