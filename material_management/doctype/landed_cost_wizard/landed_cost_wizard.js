cur_frm.cscript.onload = function(doc, cdt, cdn) {
if(!doc.currency){doc.currency = sys_defaults.currency;}
}

cur_frm.fields_dict['landed_cost_details'].grid.get_field("account_head").get_query = function(doc,cdt,cdn) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.account_type = "Chargeable" AND  tabAccount.name LIKE "%s"'
}

cur_frm.fields_dict['landed_cost_details'].grid.get_field("account_head").get_query = function(doc,cdt,cdn) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND (tabAccount.account_type = "Tax" OR tabAccount.account_type = "Chargeable") AND  tabAccount.name LIKE "%s"'
}