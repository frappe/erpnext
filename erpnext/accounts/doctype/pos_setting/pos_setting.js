cur_frm.cscript.onload = function(doc,cdt,cdn){
  $c_obj(make_doclist(cdt,cdn),'get_series','',function(r,rt){
    if(r.message) set_field_options('naming_series', r.message);
  });
 
  
}

//cash bank account
//------------------------------------
cur_frm.fields_dict['cash_bank_account'].get_query = function(doc,cdt,cdn) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

// Income Account 
// --------------------------------
cur_frm.fields_dict['income_account'].get_query = function(doc,cdt,cdn) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Credit" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.account_type ="Income Account" AND tabAccount.%(key)s LIKE "%s"'
}


// Cost Center 
// -----------------------------
cur_frm.fields_dict['cost_center'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.`docstatus`!= 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50';
}

//get query select Territory
//=================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}


// ------------------ Get Print Heading ------------------------------------
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}
