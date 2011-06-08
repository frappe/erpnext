
//========================== On Load =================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
hide_field('Repost Account Balances');
  hide_field('next_fiscal_year');
  hide_field('Repost');

  if (doc.docstatus == 1) { 
    unhide_field('Repost Account Balances');
    unhide_field('next_fiscal_year');
    unhide_field('Repost');
  }
}

// ***************** Get Account Head *****************
cur_frm.fields_dict['closing_account_head'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.is_pl_account = "No" AND `tabAccount`.debit_or_credit = "Credit" AND `tabAccount`.company = "'+ cstr(doc.company) +'" AND `tabAccount`.freeze_account = "No" AND `tabAccount`.group_or_ledger = "Ledger" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name ASC LIMIT 50';
}

cur_frm.cscript.acc_help = function(doc,dt,dn){
  show_chart_browser('Accounts Browser','Account');
}