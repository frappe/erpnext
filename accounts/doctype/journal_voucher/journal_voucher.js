cur_frm.cscript.onload = function(doc, cdt, cdn) {
  var cp = locals['Control Panel']['Control Panel'];
  
  if (!doc.voucher_date) doc.voucher_date = dateutil.obj_to_str(new Date());

  if(cp.country == 'India') {
    unhide_field(['tds_applicable','tds_category','Get TDS','tax_code','rate','ded_amount','supplier_account']);
  }
  else {
    hide_field(['tds_applicable','tds_category','Get TDS','tax_code','rate','ded_amount','supplier_account']);
  }
}

cur_frm.cscript.is_opening = function(doc, cdt, cdn) {
  hide_field('aging_date');
  if (doc.is_opening == 'Yes') unhide_field('aging_date');
  
  if(doc.docstatus==1) { unhide_field('View Ledger Entry'); }
  else hide_field('View Ledger Entry');
}

cur_frm.cscript.refresh = cur_frm.cscript.is_opening;

cur_frm.fields_dict['entries'].grid.get_field('account').get_query = function(doc) {
  return "SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.company='"+doc.company+"' AND tabAccount.group_or_ledger = 'Ledger' AND tabAccount.docstatus != 2 AND `tabAccount`.%(key)s LIKE '%s' ORDER BY `tabAccount`.name DESC LIMIT 50";
}

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.docstatus != 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50';
}

// Restrict Voucher based on Account
// ---------------------------------
cur_frm.fields_dict['entries'].grid.get_field('against_voucher').get_query = function(doc) {
  var d = locals[this.doctype][this.docname];
  return "SELECT `tabPayable Voucher`.name, `tabPayable Voucher`.credit_to, `tabPayable Voucher`.outstanding_amount,`tabPayable Voucher`.bill_no, `tabPayable Voucher`.bill_date FROM `tabPayable Voucher` WHERE `tabPayable Voucher`.credit_to='"+d.account+"' AND `tabPayable Voucher`.outstanding_amount > 0 AND `tabPayable Voucher`.docstatus = 1 AND `tabPayable Voucher`.%(key)s LIKE '%s' ORDER BY `tabPayable Voucher`.name DESC LIMIT 200";
}

cur_frm.fields_dict['entries'].grid.get_field('against_invoice').get_query = function(doc) {
  var d = locals[this.doctype][this.docname];
  return "SELECT `tabReceivable Voucher`.name, `tabReceivable Voucher`.debit_to, `tabReceivable Voucher`.outstanding_amount FROM `tabReceivable Voucher` WHERE `tabReceivable Voucher`.debit_to='"+d.account+"' AND `tabReceivable Voucher`.outstanding_amount > 0 AND `tabReceivable Voucher`.docstatus = 1 AND `tabReceivable Voucher`.%(key)s LIKE '%s' ORDER BY `tabReceivable Voucher`.name DESC LIMIT 200";
}

// TDS Account Head
cur_frm.fields_dict['tax_code'].get_query = function(doc) {
  return "SELECT `tabTDS Category Account`.account_head FROM `tabTDS Category Account` WHERE `tabTDS Category Account`.parent = '"+doc.tds_category+"' AND `tabTDS Category Account`.company='"+doc.company+"' AND `tabTDS Category Account`.account_head LIKE '%s' ORDER BY `tabTDS Category Account`.account_head DESC LIMIT 50";
}

//Set debit and credit to zero on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.idx == 1){
    d.debit = 0;
    d.credit = 0;
  }
}

// Get Outstanding of Payable & Receivable Voucher
// -----------------------------------------------

cur_frm.cscript.against_voucher = function(doc,cdt,cdn) {
  var d = locals[cdt][cdn];
  if (d.against_voucher && !flt(d.debit)) {
    args = {'doctype': 'Payable Voucher', 'docname': d.against_voucher }
    get_server_fields('get_outstanding',docstring(args),'entries',doc,cdt,cdn,1,function(r,rt) { cur_frm.cscript.update_totals(doc); });
  }
}

cur_frm.cscript.against_invoice = function(doc,cdt,cdn) {
  var d = locals[cdt][cdn];
  if (d.against_invoice && !flt(d.credit)) {
    args = {'doctype': 'Receivable Voucher', 'docname': d.against_invoice }
    get_server_fields('get_outstanding',docstring(args),'entries',doc,cdt,cdn,1,function(r,rt) { cur_frm.cscript.update_totals(doc); });
  }
}


// Update Totals
// ---------------
cur_frm.cscript.update_totals = function(doc) {
  var td=0.0; var tc =0.0;
  var el = getchildren('Journal Voucher Detail', doc.name, 'entries');
  for(var i in el) {
    td += flt(el[i].debit);
    tc += flt(el[i].credit);
  }
  var doc = locals[doc.doctype][doc.name];
  tc += flt(doc.ded_amount)
  doc.total_debit = td;
  doc.total_credit = tc;
  doc.difference = flt(td - tc);
  refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.debit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.credit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.ded_amount = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.rate = function(doc,dt,dn) {
  doc.ded_amount = doc.total_debit*doc.rate/100;
  refresh_field('ded_amount');
  cur_frm.cscript.update_totals(doc); 
}
cur_frm.cscript['Get Balance'] = function(doc,dt,dn) {
  cur_frm.cscript.update_totals(doc); 
  $c_obj(make_doclist(dt,dn), 'get_balance', '', function(r, rt){
  cur_frm.refresh();
  });
}
// Get balance
// -----------

cur_frm.cscript.account = function(doc,dt,dn) {
  var d = locals[dt][dn];
  $c_obj('GL Control','get_bal',d.account+'~~~'+doc.fiscal_year, function(r,rt) { d.balance = r.message; refresh_field('balance',d.name,'entries'); });
} 

cur_frm.cscript.validate = function(doc,cdt,cdn) {
  cur_frm.cscript.update_totals(doc);
}

// TDS
// --------
cur_frm.cscript['Get TDS'] = function(doc, dt, dn) {
  $c_obj(make_doclist(dt,dn), 'get_tds', '', function(r, rt){
    cur_frm.refresh();
    cur_frm.cscript.update_totals(doc);
  });
}

// ***************** Get Print Heading based on Receivable Voucher *****************
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}



cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
  if(doc.select_print_heading){
    // print heading
    cur_frm.pformat.print_heading = doc.select_print_heading;
  }
  else
    cur_frm.pformat.print_heading = "Journal Voucher";
}

/****************** Get Accounting Entry *****************/
cur_frm.cscript['View Ledger Entry'] = function(doc,cdt,cdn){
  var callback = function(report){
    report.set_filter('GL Entry', 'Voucher No',doc.name);
    report.dt.run();
  }
  loadreport('GL Entry','General Ledger', callback);
}
