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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.onload = function(doc,cdt,cdn){
	cur_frm.cscript.refresh(doc, cdt, cdn);
}


// get pan and tan no
cur_frm.cscript.company = function(doc,cdt,cdn){
	if(doc.company) get_server_fields('get_registration_details','','',doc,cdt,cdn);
}

// check
cur_frm.cscript.to_date = function(doc,cdt,cdn){
	if(doc.from_date && doc.to_date && (doc.from_date>doc.to_date)){
		alert("From date can not be greater than To date");
		doc.to_date='';
		refresh_field('to_date');
	}
}

cur_frm.cscript.from_date = function(doc,cdt,cdn){
	if(doc.from_date && doc.to_date && (doc.from_date>doc.to_date)){
		alert("From date can not be greater than To date");
		doc.from_date='';
		refresh_field('from_date');
	}
}

// Make Journal Voucher
// --------------------

cur_frm.cscript.make_bank_voucher = function(doc, dt, dn) {	
	var call_back = function(r,rt) {
		cur_frm.cscript.make_jv(doc,dt,dn,r.message);
	}
	// get def bank and tds account
	$c_obj(make_doclist(dt, dn), 'get_bank_and_tds_account', '', call_back);
}

cur_frm.cscript.make_jv = function(doc, dt, dn, det) {
	var jv = LocalDB.create('Journal Voucher');
	jv = locals['Journal Voucher'][jv];
	jv.voucher_type = 'Bank Voucher';
	jv.voucher_date = dateutil.obj_to_str(new Date());
	jv.posting_date = dateutil.obj_to_str(new Date());
	jv.aging_date = dateutil.obj_to_str(new Date());
	jv.remark = repl('Payment against voucher %(vn)s. %(rem)s', {vn:doc.name, rem:doc.remarks});
	jv.total_debit = doc.total_tds;
	jv.total_credit = doc.total_tds;
	jv.fiscal_year = sys_defaults.fiscal_year;
	jv.company = doc.company;

	// debit to tds account	
	var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = det.tds_account;
	d1.debit = doc.total_tds;

	// credit to bank account
	var d2 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
	d2.account = det.bank_account;
	d2.credit = doc.total_tds;
	
	loaddoc('Journal Voucher', jv.name);
}

// Show / Hide button
cur_frm.cscript.refresh = function(doc, dt, dn) {
	if(doc.docstatus==1) { 
		unhide_field('make_bank_voucher'); 
		unhide_field('update');
	}
	else {
		hide_field('make_bank_voucher');
		hide_field('update');
	} 
}
