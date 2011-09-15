$import(Production Tips Common)

cur_frm.cscript.onload = function(doc, cdt, cdn) {

   

  if (!doc.fiscal_year && doc.__islocal){ set_default_values(doc);}
  if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
  if (!doc.status) doc.status = 'Draft';
  cfn_set_fields(doc, cdt, cdn);
  if (doc.origin != "MRP"){
    doc.origin = "Manual"; 
    //get_field('Production Order', 'consider_sa_items').permlevel = 0;
    set_field_permlevel('production_item', 0);
    set_field_permlevel('bom_no', 0);
    set_field_permlevel('consider_sa_items',0);
    
  }
}
// ================================== Refresh ==========================================
cur_frm.cscript.refresh = function(doc, cdt, cdn) { 

   
  cfn_set_fields(doc, cdt, cdn);
}

cur_frm.fields_dict['production_item'].get_query = function(doc) {
   return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.`description` FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.%(key)s LIKE "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

// ---------------------- Get project name --------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}

cur_frm.fields_dict['bom_no'].get_query = function(doc)  {
  if (doc.production_item){
    return 'SELECT DISTINCT `tabBill Of Materials`.`name` FROM `tabBill Of Materials` WHERE `tabBill Of Materials`.`is_active` = "Yes" AND `tabBill Of Materials`.`item` = "' + cstr(doc.production_item) + '" AND`tabBill Of Materials`.%(key)s LIKE "%s" ORDER BY `tabBill Of Materials`.`name` LIMIT 50';
  }
  else {
    alert(" Please Enter Production Item First.")
  }
}

cur_frm.cscript.production_item = function(doc, cdt, cdn) {
  get_server_fields('get_item_detail',doc.production_item,'',doc,cdt,cdn,1);
}

var cfn_set_fields = function(doc, cdt, cdn) {
  hide_field('Material Transfer');
  hide_field('Stop Production Order');
  hide_field('Unstop Production Order')
  hide_field('Backflush');
  if (doc.docstatus == 1){
    unhide_field('Stop Production Order');
    if (doc.status == 'Submitted' || doc.status == 'Material Transferred' || doc.status == 'In Process'){
      unhide_field(['Material Transfer','Backflush']);
    }
    else if (doc.status == 'Stopped'){
      unhide_field('Unstop Production Order');
      hide_field(['Stop Production Order', 'Material Transfer', 'Backflush']);
    }
    else if (doc.status == 'Completed'){
      hide_field(['Stop Production Order', 'Material Transfer', 'Backflush']);
    }
  }
 
}

// Stop PRODUCTION ORDER
// ==================================================================================================
cur_frm.cscript['Stop Production Order'] = function(doc,cdt,cdn) {
  var check = confirm("DO YOU REALLY WANT TO Stop PRODUCTION ORDER : " + doc.name);

  if (check) {
    $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
      cur_frm.refresh();
    });	
  }
}

// Unstop PRODUCTION ORDER
// ==================================================================================================
cur_frm.cscript['Unstop Production Order'] = function(doc,cdt,cdn) {
  var check = confirm("DO YOU REALLY WANT TO Unstop PRODUCTION ORDER : " + doc.name);

  if (check) {
    $c('runserverobj', args={'method':'update_status', 'arg': 'Unstopped', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
      cur_frm.refresh();
    });	
  }
}

cur_frm.cscript['Material Transfer'] = function(doc,cdt,cdn) {
  cur_frm.cscript.make_se(doc, process = 'Material Transfer');
}

cur_frm.cscript['Backflush'] = function(doc,cdt,cdn) {
  cur_frm.cscript.make_se(doc, process = 'Backflush');
}

cur_frm.cscript.make_se = function(doc, process) {
  var se = LocalDB.create('Stock Entry');
  se = locals['Stock Entry'][se];
  se.purpose = 'Production Order';
  se.process = process;
  se.posting_date = doc.posting_date;
  se.production_order = doc.name; 
  se.fiscal_year = doc.fiscal_year;
  se.company = doc.company;
  
  loaddoc('Stock Entry', se.name);
}
