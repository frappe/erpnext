cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(doc.company)get_server_fields('get_registration_details','','',doc,cdt,cdn,1);
}

cur_frm.cscript.company = function(doc,cdt,cdn){
  if(doc.company)get_server_fields('get_registration_details','','',doc,cdt,cdn);
}

cur_frm.fields_dict['party_name'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.master_type = "Supplier" AND `tabAccount`.docstatus != 2 AND `tabAccount`.group_or_ledger = "Ledger" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name ASC LIMIT 50';
}

cur_frm.cscript.party_name = function(doc,cdt,cdn){
  if(doc.party_name)get_server_fields('get_party_det','','',doc,cdt,cdn);
}

// Date validation
cur_frm.cscript.to_date = function(doc,cdt,cdn){
  if((doc.from_date) && (doc.to_date) && (doc.from_date>doc.to_date)){
    alert("From date can not be greater than To date");
    doc.to_date='';
    refresh_field('to_date');
  }
}

cur_frm.cscript.from_date = function(doc,cdt,cdn){
  if((doc.from_date) && (doc.to_date) && (doc.from_date>doc.to_date)){
    alert("From date can not be greater than To date");
    doc.from_date='';
    refresh_field('from_date');
  }
}