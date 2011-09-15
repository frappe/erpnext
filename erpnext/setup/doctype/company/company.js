cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  if(doc.abbr && !doc.__islocal) set_field_permlevel('abbr',1);
}

cur_frm.cscript.has_special_chars = function(t) {
  var iChars = "!@#$%^*+=-[]\\\';,/{}|\":<>?";
  for (var i = 0; i < t.length; i++) {
    if (iChars.indexOf(t.charAt(i)) != -1) {
      return true;
    }
  }
  return false;
}

cur_frm.cscript.company_name = function(doc){
  if(doc.company_name && cur_frm.cscript.has_special_chars(doc.company_name)){   
    msgprint("<font color=red>Special Characters <b>! @ # $ % ^ * + = - [ ] ' ; , / { } | : < > ?</b> are not allowed for</font>\nCompany Name <b>" + doc.company_name +"</b>")        
    doc.company_name = '';
    refresh_field('company_name');
  }
}

cur_frm.cscript.abbr = function(doc){
  if(doc.abbr && cur_frm.cscript.has_special_chars(doc.abbr)){   
    msgprint("<font color=red>Special Characters <b>! @ # $ % ^ * + = - [ ] ' ; , / { } | : < > ?</b> are not allowed for</font>\nAbbr <b>" + doc.abbr +"</b>")        
    doc.abbr = '';
    refresh_field('abbr');
  }
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
