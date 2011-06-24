cur_frm.cscript.tname = "PO Detail";
cur_frm.cscript.fname = "po_details";
cur_frm.cscript.other_fname = "purchase_tax_details";
$import(Purchase Common)
$import(Purchase Other Charges)
$import(SMS Control)

//========================== On Load =================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {

  if(!doc.fiscal_year && doc.__islocal){ //set_default_values(doc);
    doc.fiscal_year = sys_defaults.fiscal_year;
  }
  if(!doc.conversion_rate) doc.conversion_rate = 1;
  if(!doc.currency) doc.currency = sys_defaults.currency;
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.transaction_date) set_multiple(cdt,cdn,{transaction_date:get_today()});
  
  if(doc.__islocal){
    hide_field(['supplier_name','supplier_address','contact_person','address_display','contact_display','contact_mobile','contact_email']);
  }
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
  if(doc.__islocal){ 
    cur_frm.cscript.get_default_schedule_date(doc);
  }	
}

// ================================== Refresh ==========================================
cur_frm.cscript.refresh = function(doc, cdt, cdn) { 

  // Show buttons
  // ---------------------------------
  cur_frm.clear_custom_buttons();
  if(doc.docstatus == 1 && doc.status != 'Stopped'){
    var ch = getchildren('PO Detail',doc.name,'po_details');
    var allow_billing = 0; var allow_receipt = 0;
    cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);

    for(var i in ch){
      if(ch[i].qty > ch[i].received_qty) allow_receipt = 1; 
      if(ch[i].qty > ch[i].billed_qty) allow_billing = 1;
    }
    if(allow_receipt)
      cur_frm.add_custom_button('Make Purchase Receipt', cur_frm.cscript['Make Purchase Receipt']);
	    
	if(allow_billing)
      cur_frm.add_custom_button('Make Invoice', cur_frm.cscript['Make Purchase Invoice']);

    if(allow_billing || allow_receipt)
      cur_frm.add_custom_button('Stop', cur_frm.cscript['Stop Purchase Order']);
  }
    
  if(doc.docstatus == 1 && doc.status == 'Stopped')
    cur_frm.add_custom_button('Unstop Purchase Order', cur_frm.cscript['Unstop Purchase Order']);

  if(doc.docstatus == 1) unhide_field(['Repair Purchase Order']);
  else hide_field(['Repair Purchase Order']);
}



//Supplier
cur_frm.cscript.supplier = function(doc,dt,dn) {
  if(doc.supplier) get_server_fields('get_default_supplier_address', JSON.stringify({supplier: doc.supplier}),'', doc, dt, dn, 1);
  if(doc.supplier) unhide_field(['supplier_name','supplier_address','contact_person','address_display','contact_display','contact_mobile','contact_email']);
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





//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
  tn = createLocal('Contact');
  locals['Contact'][tn].is_supplier = 1;
  if(doc.supplier) locals['Contact'][tn].supplier = doc.supplier;
  loaddoc('Contact', tn);
}

//======================= transaction date =============================
cur_frm.cscript.transaction_date = function(doc,cdt,cdn){
  if(doc.__islocal){ 
    cur_frm.cscript.get_default_schedule_date(doc);
  }
}


// ---------------------- Get project name --------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


//==================== Indent No Get Query =======================================================
//===== Only those Indents status != 'Completed' and docstatus = 1 i.e. submitted=================
cur_frm.fields_dict['indent_no'].get_query = function(doc) {
  return 'SELECT DISTINCT `tabIndent`.`name` FROM `tabIndent` WHERE `tabIndent`.company = "' + doc.company + '" and `tabIndent`.`docstatus` = 1 and `tabIndent`.`status` != "Stopped" and ifnull(`tabIndent`.`per_ordered`,0) < 100 and `tabIndent`.%(key)s LIKE "%s" ORDER BY `tabIndent`.`name` DESC LIMIT 50';
}

/*
//*********** get approved supplier quotation ********************
cur_frm.fields_dict['supplier_qtn'].get_query = function(doc) {
  var cond='';
  if(doc.supplier) cond = 'ifnull(`tabSupplier Quotation`.supplier, "") = "'+doc.supplier+'" and';
  
  return repl('SELECT DISTINCT `tabSupplier Quotation`.`name` FROM `tabSupplier Quotation` WHERE `tabSupplier Quotation`.company = "%(company)s" and`tabSupplier Quotation`.`docstatus` = 1 and `tabSupplier Quotation`.`approval_status` = "Approved" and %(cond)s `tabSupplier Quotation`.%(key)s LIKE "%s" ORDER BY `tabSupplier Quotation`.`name` DESC LIMIT 50', {company:doc.company,cond:cond});
}
*/


//========================= Get Last Purhase Rate =====================================
cur_frm.cscript['Get Last Purchase Rate'] = function(doc, cdt, cdn){
  $c_obj(make_doclist(doc.doctype, doc.name), 'get_last_purchase_rate', '', 
      function(r, rt) { 
        refresh_field(cur_frm.cscript.fname);
        var doc = locals[cdt][cdn];
        cur_frm.cscript.calc_amount( doc, 2);
      }
  );

}

//========================= Make Purchase Receipt =======================================================
cur_frm.cscript['Make Purchase Receipt'] = function() {
  n = createLocal('Purchase Receipt');
  $c('dt_map', args={
    'docs':compress_doclist([locals['Purchase Receipt'][n]]),
    'from_doctype': cur_frm.doc.doctype,
    'to_doctype':'Purchase Receipt',
    'from_docname':cur_frm.doc.name,
    'from_to_list':"[['Purchase Order','Purchase Receipt'],['PO Detail','Purchase Receipt Detail'],['Purchase Tax Detail','Purchase Tax Detail']]"
    }, function(r,rt) {
       loaddoc('Purchase Receipt', n);
    }
  );
}

//========================== Make Purchase Invoice =====================================================
cur_frm.cscript['Make Purchase Invoice'] = function() {
  n = createLocal('Payable Voucher');
  $c('dt_map', args={
    'docs':compress_doclist([locals['Payable Voucher'][n]]),
    'from_doctype':cur_frm.doc.doctype,
    'to_doctype':'Payable Voucher',
    'from_docname': cur_frm.doc.name,
    'from_to_list':"[['Purchase Order','Payable Voucher'],['PO Detail','PV Detail'],['Purchase Tax Detail','Purchase Tax Detail']]"
    }, function(r,rt) {
       loaddoc('Payable Voucher', n);
    }
  );
}


// Stop PURCHASE ORDER
// ==================================================================================================
cur_frm.cscript['Stop Purchase Order'] = function() {
  var doc = cur_frm.doc;
  var check = confirm("Do you really want to STOP " + doc.name);

  if (check) {
    $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
      cur_frm.refresh();
    });	
  }
}

// Unstop PURCHASE ORDER
// ==================================================================================================
cur_frm.cscript['Unstop Purchase Order'] = function() {
  var doc = cur_frm.doc;
  var check = confirm("Do you really want to UNSTOP " + doc.name);

  if (check) {
    $c('runserverobj', args={'method':'update_status', 'arg': 'Submitted', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
      cur_frm.refresh();
    });	
  }
}

// ***************** Get Print Heading  *****************
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}
//****************** For print sales order no and date*************************
cur_frm.pformat.indent_no = function(doc, cdt, cdn){
  //function to make row of table
  
  var make_row = function(title,val1, val2, bold){
    var bstart = '<b>'; var bend = '</b>';

    return '<tr><td style="width:39%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
     +'<td style="width:61%;text-align:left;">'+val1+(val2?' ('+dateutil.str_to_user(val2)+')':'')+'</td>'
     +'</tr>'
  }

  out ='';
  
  var cl = getchildren('PO Detail',doc.name,'po_details');

  // outer table  
  var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 50%"></td><td>';
  
  // main table
  out +='<table class="noborder" style="width:100%">';

  // add rows
  if(cl.length){
    prevdoc_list = new Array();
    for(var i=0;i<cl.length;i++){
      if(cl[i].prevdoc_doctype == 'Indent' && cl[i].prevdoc_docname && prevdoc_list.indexOf(cl[i].prevdoc_docname) == -1) {
        prevdoc_list.push(cl[i].prevdoc_docname);
        if(prevdoc_list.length ==1)
          out += make_row(cl[i].prevdoc_doctype, cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
        else
          out += make_row('', cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
      }
    }
  }

  out +='</table></td></tr></table></div>';

  return out;
}
