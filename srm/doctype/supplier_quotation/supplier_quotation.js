cur_frm.cscript.tname = "Supplier Quotation Detail";
cur_frm.cscript.fname = "supplier_quotation_details";

$import(Purchase Common)

// ======================= OnLoad =============================================
cur_frm.cscript.onload = function(doc,cdt,cdn){

  
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.transaction_date) set_multiple(cdt,cdn,{transaction_date:get_today()});
  if(!doc.conversion_rate) set_multiple(cdt,cdn,{conversion_rate:'1'});
  if(!doc.currency) set_multiple(cdt,cdn,{currency:sys_defaults.currency});
  
  if(doc.__islocal && has_common(user_roles,['Partner','Supplier'])){
    get_server_fields('get_contact_details','','',doc,cdt,cdn,1);
  }
  else if(doc.__islocal && doc.supplier){
    get_server_fields('get_supplier_details',doc.supplier,'',doc,cdt,cdn,1);
  }

}

//======================= Refresh ==============================================
cur_frm.cscript.refresh = function(doc,cdt,cdn){

  if(has_common(user_roles,['Purchase User','Purchase Manager'])){
    unhide_field(['Approve / Unapprove']);
    if(doc.approval_status == 'Approved' && doc.status == 'Submitted') { unhide_field(['Create PO']);}
    else { hide_field(['Create PO']);}
  }
  else{ 
    hide_field(['Create PO']);
    hide_field(['Approve / Unapprove']);
  }  
}

//======================= RFQ NO Get Query ===============================================
cur_frm.fields_dict['rfq_no'].get_query = function(doc){
  return 'SELECT DISTINCT `tabRFQ`.name FROM `tabRFQ` WHERE `tabRFQ`.docstatus = 1 AND `tabRFQ`.name LIKE "%s"';
}

// ***************** Get Contact Person based on supplier selected *****************
cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabContact`.contact_name FROM `tabContact` WHERE `tabContact`.is_supplier = 1 AND `tabContact`.supplier = "'+ doc.supplier+'" AND `tabContact`.docstatus != 2 AND `tabContact`.docstatus != 2 AND `tabContact`.contact_name LIKE "%s" ORDER BY `tabContact`.contact_name ASC LIMIT 50';
}

//=================== On Button Click Functions =====================

//======================== Create Purchase Order =========================================
cur_frm.cscript['Create PO'] = function(doc,cdt,cdn){
  n = createLocal("Purchase Order");
  $c('dt_map', args={
    'docs':compress_doclist([locals["Purchase Order"][n]]),
    'from_doctype':'Supplier Quotation',
    'to_doctype':'Purchase Order',
    'from_docname':doc.name,
    'from_to_list':"[['Supplier Quotation', 'Purchase Order'], ['Supplier Quotation Detail', 'PO Detail']]"
  }
  , function(r,rt) {
      loaddoc("Purchase Order", n);
    }
  );
}

//======================== Get Report ===================================================
cur_frm.cscript['Get Report'] = function(doc,cdt,cdn) {
  var callback = function(report){
  report.set_filter('PO Detail', 'Ref Doc',doc.name)
 }
 loadreport('PO Detail','Itemwise Purchase Details', callback);
}

cur_frm.cscript['Approve / Unapprove'] = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  
  $c_obj(make_doclist(doc.doctype, doc.name),'update_approval_status','', function(r,rt){  
    refresh_field('approval_status');
    doc.approval_status = r.message;
    cur_frm.cscript.refresh(d, d.cdt, d.cdn);
  });
}