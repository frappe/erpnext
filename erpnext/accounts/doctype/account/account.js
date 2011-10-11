// Fetch parent details
// -----------------------------------------
cur_frm.add_fetch('parent_account', 'debit_or_credit', 'debit_or_credit');
cur_frm.add_fetch('parent_account', 'is_pl_account', 'is_pl_account');

// Hide tax rate based on account type
// -----------------------------------------
cur_frm.cscript.account_type = function(doc, cdt, cdn) {
  if(doc.account_type == 'Tax') unhide_field(['tax_rate']);
  else hide_field(['tax_rate']);
}

// Onload
// -----------------------------------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  cur_frm.cscript.account_type(doc, cdt, cdn);
  // hide India specific fields
  var cp = locals['Control Panel']['Control Panel'];
  if(cp.country == 'India')
    unhide_field(['pan_number', 'tds_applicable', 'tds_details', 'TDS']);
  else
    hide_field(['pan_number', 'tds_applicable', 'tds_details', 'TDS']);
}

// Refresh
// -----------------------------------------
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  root_acc = ['	Application of Funds (Assets)','Expenses','Income','Source of Funds (Liabilities)'];
  if(inList(root_acc, doc.account_name))
    cur_frm.perm = [[1,0,0], [1,0,0]];
  cur_frm.cscript.hide_unhide_group_ledger(doc);
}

// Hide/unhide group or ledger
// -----------------------------------------
cur_frm.cscript.hide_unhide_group_ledger = function(doc) {
  hide_field(['Convert to Group', 'Convert to Ledger']);
  if (cstr(doc.group_or_ledger) == 'Group') unhide_field('Convert to Ledger');
  else if (cstr(doc.group_or_ledger) == 'Ledger') unhide_field('Convert to Group');
}

// Convert group to ledger
// -----------------------------------------
cur_frm.cscript['Convert to Ledger'] = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn),'convert_group_to_ledger','',function(r,rt) {
    if(r.message == 1) {
      doc.group_or_ledger = 'Ledger';
      refresh_field('group_or_ledger');
      cur_frm.cscript.hide_unhide_group_ledger(doc);
    }
  });
}

// Convert ledger to group
// -----------------------------------------
cur_frm.cscript['Convert to Group'] = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn),'convert_ledger_to_group','',function(r,rt) {
    if(r.message == 1) {
      doc.group_or_ledger = 'Group';
      refresh_field('group_or_ledger');
      cur_frm.cscript.hide_unhide_group_ledger(doc);
    }
  });
}

// Master name get query
// -----------------------------------------
cur_frm.fields_dict['master_name'].get_query=function(doc){
 if (doc.master_type){
    return 'SELECT `tab'+doc.master_type+'`.name FROM `tab'+doc.master_type+'` WHERE `tab'+doc.master_type+'`.name LIKE "%s" and `tab'+doc.master_type+'`.docstatus != 2 ORDER BY `tab'+doc.master_type+'`.name LIMIT 50';
  }
  else alert("Please select master type");
}

// parent account get query
// -----------------------------------------
cur_frm.fields_dict['parent_account'].get_query = function(doc){
  return 'SELECT DISTINCT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.group_or_ledger="Group" AND `tabAccount`.docstatus != 2 AND `tabAccount`.company="'+ doc.company+'" AND `tabAccount`.company is not NULL AND `tabAccount`.name LIKE "%s" ORDER BY `tabAccount`.name LIMIT 50';
}
