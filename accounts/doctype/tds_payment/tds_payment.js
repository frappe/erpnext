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

cur_frm.cscript['Make Bank Voucher'] = function(doc, dt, dn) {  
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
    unhide_field('Make Bank Voucher'); 
    unhide_field('Update');
  }
  else {
    hide_field('Make Bank Voucher');
    hide_field('Update');
  } 
}
