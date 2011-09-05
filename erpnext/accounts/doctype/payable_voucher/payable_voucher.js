cur_frm.cscript.tname = "PV Detail";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "purchase_tax_details";
$import(Purchase Other Charges)
$import(Purchase Common)

// On Load
// --------
cur_frm.cscript.onload = function(doc,dt,dn) {
  var cp = locals['Control Panel']['Control Panel'];
  
  if(!doc.voucher_date) set_multiple(dt,dn,{voucher_date:get_today()});
  if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});  

  if(cp.country == 'India') {
    unhide_field(['TDS','tds_applicable','tds_category','Get TDS','tax_code','rate','ded_amount','total_tds_on_voucher','tds_amount_on_advance']);
  }
  else {
    hide_field(['TDS','tds_applicable','tds_category','Get TDS','tax_code','rate','ded_amount','total_tds_on_voucher','tds_amount_on_advance']);
  }  
  
  if(doc.__islocal){
    if(doc.supplier) {cur_frm.cscript.supplier(doc,dt,dn)}
    hide_field(['supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email']);
  }
  

  if(doc.supplier) unhide_field(['supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email']);  
}

// Refresh
// --------
cur_frm.cscript.refresh = function(doc, dt, dn) {
  
  cur_frm.clear_custom_buttons();

  // Show / Hide button
  if(doc.docstatus==1 && doc.outstanding_amount > 0)
    cur_frm.add_custom_button('Make Payment Entry', cur_frm.cscript['Make Bank Voucher']);
  
  if(doc.docstatus==1) { 
    unhide_field(['Repair Outstanding Amt']); 
    cur_frm.add_custom_button('View Ledger', cur_frm.cscript['View Ledger Entry']);
  } else hide_field(['Repair Outstanding Amt']);
  
  cur_frm.cscript.is_opening(doc, dt, dn);
}


//Supplier
cur_frm.cscript.supplier = function(doc,dt,dn) {

  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];    
      get_server_fields('get_credit_to','','',doc, dt, dn, 0, callback2);
  }
  
  var callback2 = function(r,rt){
    var doc = locals[cur_frm.doctype][cur_frm.docname];    
    var el = getchildren('PV Detail',doc.name,'entries');
    for(var i in el){
      if(el[i].item_code && (!el[i].expense_head || !el[i].cost_center)){
        args = "{'item_code':'" + el[i].item_code + "','expense_head':'" + el[i].expense_head + "','cost_center':'" + el[i].cost_center + "'}";
        get_server_fields('get_default_values', args, 'entries', doc, el[i].doctype, el[i].name, 1);
      }
    }
    cur_frm.cscript.calc_total(doc);
  }

  if(doc.supplier) get_server_fields('get_default_supplier_address', JSON.stringify({supplier: doc.supplier}),'', doc, dt, dn, 1,callback);
  if(doc.supplier) unhide_field(['supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email']);
}

cur_frm.cscript.supplier_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {
  if(doc.supplier) get_server_fields('get_supplier_address', JSON.stringify({supplier: doc.supplier, address: doc.supplier_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,address_line1,city FROM tabAddress WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}


cur_frm.fields_dict.supplier_address.on_new = function(dn) {
  locals['Address'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
  locals['Address'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
  locals['Contact'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
  locals['Contact'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}


cur_frm.cscript.credit_to = function(doc,dt,dn) {

  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];    
      if(doc.supplier) get_server_fields('get_default_supplier_address', JSON.stringify({supplier: doc.supplier}),'', doc, dt, dn, 1);
      if(doc.supplier) unhide_field(['supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email']);
      cur_frm.refresh();
  }

  get_server_fields('get_cust','','',doc,dt,dn,1,callback);  
}



// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}


//Set expense_head and cost center on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
  
  cl = getchildren('PV Detail', doc.name, cur_frm.cscript.fname, doc.doctype);
  acc = '';
  cc = '';

  for(var i = 0; i<cl.length; i++) {
    if (cl[i].idx == 1){
      acc = cl[i].expense_head;
      cc = cl[i].cost_center;
    }
    else{
      if (! cl[i].expense_head) { cl[i].expense_head = acc; refresh_field('expense_head', cl[i].name, 'entries');}
      if (! cl[i].cost_center)  {cl[i].cost_center = cc; refresh_field('cost_center', cl[i].name, 'entries');}
    }
  }
}

cur_frm.cscript.is_opening = function(doc, dt, dn) {
  hide_field('aging_date');
  if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

/* ******************************** TRIGGERS **************************************** */
/*
// Supplier
// ---------
cur_frm.cscript.supplier = function(doc,cdt,cdn){
  get_server_fields('get_credit_to','','',doc,cdt,cdn);
}
*/

// Conversion Rate
// ----------------
cur_frm.cscript.conversion_rate = function(doc,cdt,cdn) {
  cur_frm.cscript.calc_total(doc,cdt,cdn);
}

// Recalculate Button
// -------------------
cur_frm.cscript['Recalculate'] = function(doc, dt, dn) {
  cur_frm.cscript.calc_total(doc, cdt, cdn);
  calc_total_advance(doc,cdt,cdn);
}

// Get Items Button
// -----------------
cur_frm.cscript['Get Items'] = function(doc, dt, dn) {
  var callback = function(r,rt) { 
	  unhide_field(['supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email']);			  
	  refresh_many(['credit_to','supplier','supplier_address','contact_person','supplier_name','address_display','contact_display','contact_mobile','contact_email','entries','purchase_receipt_main','purchase_order_main']);
  }
  get_server_fields('pull_details','','',doc, dt, dn,1,callback);
}


// ========== PV Details Table ============

// Item Code
// ----------
cur_frm.cscript.item_code = function(doc,cdt,cdn){
  var d = locals[cdt][cdn];
  if(d.item_code){
    get_server_fields('get_item_details',d.item_code,'entries',doc,cdt,cdn,1);
  }
}

// Quantity
// ---------
cur_frm.cscript.qty  = function(doc,dt,dn) { cur_frm.cscript.calc_exp_row(doc,dt,dn); }

// Import Rate
// ------------
cur_frm.cscript.import_rate = function(doc,dt,dn) {
  var d = locals[dt][dn];
  set_multiple('PV Detail', d.name, {'rate': flt(d.import_rate) * flt(doc.conversion_rate) }, 'entries');
  cur_frm.cscript.calc_exp_row(doc,dt,dn)
}


// ============== TDS ===============

// Rate in Deduct Taxes (TDS)
// --------------------------
cur_frm.cscript.rate = function(doc,dt,dn) {
  //This is done as Purchase tax detail and PV detail both contain the same fieldname 'rate'
  if(dt != 'Purchase Tax Detail') cur_frm.cscript.calc_exp_row(doc,dt,dn); 
}

// Amount
// -------
cur_frm.cscript.ded_amount = function(doc,dt,dn) { cur_frm.cscript.calc_total(doc); }

// Get TDS Button
// ---------------
cur_frm.cscript['Get TDS'] = function(doc, dt, dn) {
  var callback = function(r,rt) {
    cur_frm.refresh();
    refresh_field('ded_amount');
    cur_frm.cscript.calc_total(locals[dt][dn]);
  }
  $c_obj(make_doclist(dt,dn), 'get_tds', '', callback);
}

// ===================== Advance Allocation ==================
cur_frm.cscript.allocated_amount = function(doc,cdt,cdn){
  var d = locals[cdt][cdn];
  if (d.allocated_amount && d.tds_amount){
    d.tds_allocated=flt(d.tds_amount*(d.allocated_amount/d.advance_amount))
    refresh_field('tds_allocated', d.name, 'advance_allocation_details');
  }
  tot_tds=0
  el = getchildren('Advance Allocation Detail',doc.name,'advance_allocation_details')
  for(var i in el){
    tot_tds += el[i].tds_allocated
  }
  doc.tds_amount_on_advance = tot_tds
  refresh_field('tds_amount_on_advance');
  
  calc_total_advance(doc, cdt, cdn);
}


// Make Journal Voucher
// --------------------
cur_frm.cscript['Make Bank Voucher'] = function(doc, dt, dn) {
  cur_frm.cscript.make_jv(cur_frm.doc);
}


/* ***************************** GET QUERY Functions *************************** */

// Item Code
// ----------
cur_frm.fields_dict['entries'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
  return 'SELECT tabItem.name, tabItem.description FROM tabItem WHERE tabItem.is_purchase_item="Yes" AND (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND tabItem.%(key)s LIKE "%s" LIMIT 50'
}

// Credit To
// ----------
cur_frm.fields_dict['credit_to'].get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Credit" AND tabAccount.is_pl_account="No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}


// Purchase Order
// ---------------
cur_frm.fields_dict['purchase_order_main'].get_query = function(doc) {
  if (doc.supplier){
    return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.supplier = "'+ doc.supplier +'" AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`,0) < 100 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
  } else {
    return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`, 0) < 100 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
  }
}

// Purchase Receipt
// -----------------
cur_frm.fields_dict['purchase_receipt_main'].get_query = function(doc) {
  if (doc.supplier){
    return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.supplier = "'+ doc.supplier +'" AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 100 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
  } else {
    return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 100 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
  }
}

// ================== PV Details Table ===================
// Expense Head
// -------------
cur_frm.fields_dict['entries'].grid.get_field("expense_head").get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"';
}
cur_frm.cscript.expense_head = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.idx == 1 && d.expense_head){
    var cl = getchildren('PV Detail', doc.name, 'entries', doc.doctype);
    for(var i = 0; i < cl.length; i++){
      if(!cl[i].expense_head) cl[i].expense_head = d.expense_head;
    }
  }
  refresh_field('entries');
}


// Cost Center
//-------------
cur_frm.fields_dict['entries'].grid.get_field("cost_center").get_query = function(doc) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.docstatus != 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50';
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.idx == 1 && d.cost_center){
    var cl = getchildren('PV Detail', doc.name, 'entries', doc.doctype);
    for(var i = 0; i < cl.length; i++){
      if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
    }
  }
  refresh_field('entries');
}


// TDS Account Head
cur_frm.fields_dict['tax_code'].get_query = function(doc) {
  return "SELECT `tabTDS Category Account`.account_head FROM `tabTDS Category Account` WHERE `tabTDS Category Account`.parent = '"+doc.tds_category+"' AND `tabTDS Category Account`.company='"+doc.company+"' AND `tabTDS Category Account`.account_head LIKE '%s' ORDER BY `tabTDS Category Account`.account_head DESC LIMIT 50";
}

cur_frm.cscript.tax_code = function(doc, dt, dn) {
  get_server_fields('get_tds_rate','','',doc, dt, dn, 0);
}

/* ***************************** UTILITY FUNCTIONS ************************ */

// Calculate
// ---------
cur_frm.cscript.calc_total = function(doc) {
  
   // expense
  var t_exp = 0.0;
  var el = getchildren('PV Detail',doc.name,'entries');
  for(var i in el) {
   if (flt(el[i].import_rate) > 0){
     set_multiple('PV Detail', el[i].name, {'rate': flt(doc.conversion_rate) * flt(el[i].import_rate) }, 'entries');
     set_multiple('PV Detail', el[i].name, {'import_amount': flt(el[i].qty) * flt(el[i].import_rate) }, 'entries');
   }
   set_multiple('PV Detail', el[i].name, {'amount': flt(el[i].qty) * flt(el[i].rate) }, 'entries')
   t_exp += flt(el[i].amount);
  }
  doc.net_total = flt(t_exp);
  refresh_field('net_total');
  cur_frm.cscript.val_cal_charges(doc, cdt, cdn, cur_frm.cscript.tname, cur_frm.cscript.fname, cur_frm.cscript.other_fname);
}


// Calculate Advance
// ------------------
var calc_total_advance = function(doc,cdt,cdn) {
  var doc = locals[doc.doctype][doc.name];
  var el = getchildren('Advance Allocation Detail',doc.name,'advance_allocation_details')
  var tot_tds=0;
  var total_advance = 0;
  for(var i in el) {
    if (! el[i].allocated_amount == 0) {
      total_advance += flt(el[i].allocated_amount);
      tot_tds += flt(el[i].tds_allocated)
    }
  }
  doc.total_amount_to_pay = flt(doc.grand_total) - flt(doc.ded_amount);
  doc.tds_amount_on_advance = flt(tot_tds);
  doc.total_advance = flt(total_advance);
  doc.outstanding_amount = flt(doc.total_amount_to_pay) - flt(total_advance);
  refresh_many(['total_advance','outstanding_amount','tds_amount_on_advance', 'total_amount_to_pay']);
}


cur_frm.cscript.calc_exp_row = function(doc,dt,dn) {
  var d = locals[dt][dn];
  d.amount = flt(d.qty * d.rate);
  refresh_field('amount',dn,'entries');
  
  if (!doc.conversion_rate){ doc.conversion_rate = 1; refresh_field('conversion_rate'); }
  
  set_multiple('PV Detail', dn, {'import_rate': flt(d.rate) / flt(doc.conversion_rate) }, 'entries');
  set_multiple('PV Detail', dn, {'import_amount': flt(d.qty) * flt(d.rate) / flt(doc.conversion_rate) }, 'entries');
  
  cur_frm.cscript.calc_total(doc)
}


// Make JV
// --------
cur_frm.cscript.make_jv = function(doc, dt, dn, det) {
  var jv = LocalDB.create('Journal Voucher');
  jv = locals['Journal Voucher'][jv];
  jv.voucher_type = 'Bank Voucher';
  //jv.voucher_series = det.def_bv_series;
  //jv.voucher_date = doc.voucher_date;
  //jv.posting_date = doc.posting_date;
  jv.remark = repl('Payment against voucher %(vn)s for %(rem)s', {vn:doc.name, rem:doc.remarks});
  jv.total_debit = doc.outstanding_amount;
  jv.total_credit = doc.outstanding_amount;
  jv.fiscal_year = doc.fiscal_year;
  jv.company = doc.company;
  
  // debit to creditor
  var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
  d1.account = doc.credit_to;
  d1.debit = doc.outstanding_amount;
  //d1.balance = det.acc_balance;
  d1.against_voucher = doc.name;
  
  // credit to bank
  var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
  //d1.account = det.def_bank_account;
  //d1.balance = det.bank_balance;
  d1.credit = doc.outstanding_amount;
  
  loaddoc('Journal Voucher', jv.name);
}

// ***************** Get project name *****************
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
  if(doc.select_print_heading){
    // print heading
    cur_frm.pformat.print_heading = doc.select_print_heading;
  }
  else
    cur_frm.pformat.print_heading = "Purchase Invoice";
}

/* *********************** Client Side Validation **************************** */
// Validate
// ---------
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  is_item_table(doc,cdt,cdn);
  cur_frm.cscript.calc_total(doc, cdt, cdn);
  calc_total_advance(doc, cdt, cdn);
}

/****************** Get Accounting Entry *****************/
cur_frm.cscript['View Ledger Entry'] = function(){
  var callback = function(report){
    report.set_filter('GL Entry', 'Voucher No',cur_frm.doc.name);
    report.dt.run();
  }
  loadreport('GL Entry','General Ledger', callback);
}
