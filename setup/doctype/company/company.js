cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  if(doc.abbr && !doc.__islocal) set_field_permlevel('abbr',1);
}

cur_frm.fields_dict.default_bank_account.get_query = function(doc) {    
  return 'SELECT `tabAccount`.name, `tabAccount`.debit_or_credit, `tabAccount`.group_or_ledger FROM `tabAccount` WHERE `tabAccount`.company = "'+doc.name+'" AND `tabAccount`.group_or_ledger = "Ledger" AND `tabAccount`.docstatus != 2 AND `tabAccount`.account_type = "Bank or Cash" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name LIMIT 50';   
}


cur_frm.fields_dict.receivables_group.get_query = function(doc) {  
  return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.company = "'+doc.name+'" AND `tabAccount`.group_or_ledger = "Group" AND `tabAccount`.docstatus != 2 AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name LIMIT 50';
}


cur_frm.fields_dict.payables_group.get_query = function(doc) {  
  return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.company = "'+doc.name+'" AND `tabAccount`.group_or_ledger = "Group" AND `tabAccount`.docstatus != 2 AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name LIMIT 50';
}
