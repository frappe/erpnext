$import(SMS Control)

cur_frm.cscript.refresh = function(doc, cdt, cdn){

  // 

  if(!doc.docstatus){
    hide_field(['Update Follow up']);
    hide_field(['email_id1','cc_to','subject','message','Attachment Html', 'Create New File', 'enquiry_attachment_detail','Send Email']);
  }
  else{
    unhide_field(['Update Follow up']);
    unhide_field(['email_id1','cc_to','subject','message','Attachment Html', 'Create New File', 'enquiry_attachment_detail','Send Email']);
  }

  
  cur_frm.clear_custom_buttons();
  if(doc.docstatus == 1) {
    cur_frm.add_custom_button('Create Quotation', cur_frm.cscript['Create Quotation']);
    cur_frm.add_custom_button('Enquiry Lost', cur_frm.cscript['Declare Enquiry Lost']);
    cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
  }

  //cur_frm.cscript.clear_values(doc,cdt,cdn);
}

// ONLOAD
// ===============================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {

  if(!doc.enquiry_from) hide_field(['customer', 'customer_address', 'contact_person', 'customer_name','lead', 'lead_name', 'address_display', 'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']);
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.date) doc.transaction_date = date.obj_to_str(new Date());
  if(!doc.company && sys_defaults.company) set_multiple(cdt,cdn,{company:sys_defaults.company});
  if(!doc.fiscal_year && sys_defaults.fiscal_year) set_multiple(cdt,cdn,{fiscal_year:sys_defaults.fiscal_year});    
  
  if(doc.enquiry_from) {
    if(doc.enquiry_from == 'Customer') {
      hide_field(['lead', 'lead_name']);
    }
    else if (doc.enquiry_from == 'Lead') {
      hide_field(['customer', 'customer_address', 'contact_person', 'customer_name', 'contact_display', 'customer_group']);
    }
  } 

  // setup fetch
  cur_frm.cscript.set_fetch();
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.enquiry_from == 'Lead' && doc.lead) {
	 	cur_frm.cscript.lead(doc,cdt,cdn);
	}
}

// fetch
// ===============================================================
cur_frm.cscript.set_fetch = function() {

  // item
  cur_frm.add_fetch('item_code', 'item_name', 'item_name');
  cur_frm.add_fetch('item_code', 'stock_uom', 'uom');
  cur_frm.add_fetch('item_code', 'description', 'description');
  cur_frm.add_fetch('item_code', 'item_group', 'item_group');
  cur_frm.add_fetch('item_code', 'brand', 'brand');

  // customer

}

// hide - unhide fields on basis of enquiry_from lead or customer
cur_frm.cscript.enquiry_from = function(doc,cdt,cdn){
  cur_frm.cscript.lead_cust_show(doc,cdt,cdn);
}

// hide - unhide fields based on lead or customer
cur_frm.cscript.lead_cust_show = function(doc,cdt,cdn){
  if(doc.enquiry_from == 'Lead'){
    unhide_field(['lead']);
    hide_field(['lead_name','customer','customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
    doc.lead = doc.lead_name = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
  }
  else if(doc.enquiry_from == 'Customer'){    
    unhide_field(['customer']);
    hide_field(['lead','lead_name','address_display','contact_display','contact_mobile','contact_email','territory']);    
    doc.lead = doc.lead_name = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
  }
}

// customer
cur_frm.cscript.customer = function(doc,dt,dn) {
  if(doc.customer) get_server_fields('get_default_customer_address', JSON.stringify({customer: doc.customer}),'', doc, dt, dn, 1);
  if(doc.customer) unhide_field(['customer_name','customer_address','contact_person','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {    
  if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict.customer_address.on_new = function(dn) {
  locals['Address'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
  locals['Address'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
  locals['Contact'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
  locals['Contact'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,address_line1,city FROM tabAddress WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

// lead
cur_frm.fields_dict['lead'].get_query = function(doc,cdt,cdn){
  return 'SELECT `tabLead`.name, `tabLead`.lead_name FROM `tabLead` WHERE `tabLead`.%(key)s LIKE "%s"  ORDER BY  `tabLead`.`name` ASC LIMIT 50';
}

cur_frm.cscript.lead = function(doc, cdt, cdn) {
  if(doc.lead) get_server_fields('get_lead_details', doc.lead,'', doc, cdt, cdn, 1);
  if(doc.lead) unhide_field(['lead_name','address_display','contact_mobile','contact_email','territory']);  
}


//item getquery
//=======================================
cur_frm.fields_dict['enquiry_details'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
  if (doc.enquiry_type == 'Maintenance')
    return 'SELECT tabItem.name,tabItem.item_name,tabItem.description FROM tabItem WHERE tabItem.is_service_item="Yes" AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") AND tabItem.%(key)s LIKE "%s" LIMIT 50';
  else 
    return 'SELECT tabItem.name,tabItem.item_name,tabItem.description FROM tabItem WHERE tabItem.is_sales_item="Yes" AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") AND tabItem.%(key)s LIKE "%s" LIMIT 50';
}
  
 //Fetch Item Details
//====================================================================================================================
cur_frm.cscript.item_code = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if (d.item_code) {
    get_server_fields('get_item_details',d.item_code,'enquiry_details',doc,cdt,cdn,1);
  }
}

/*
 //Fetch Customer Details
//======================================================================================================================
cur_frm.cscript.customer = function(doc, cdt, cdn){
  if (doc.customer) {
    get_server_fields('get_cust_address',doc.customer,'',doc,cdt,cdn,1);
  }
}
*/

/*
//=======================================================================================================================
cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabContact`.contact_name FROM `tabContact` WHERE `tabContact`.is_customer = 1 AND `tabContact`.customer = "'+ doc.customer+'" AND `tabContact`.docstatus != 2 AND `tabContact`.contact_name LIKE "%s" ORDER BY `tabContact`.contact_name ASC LIMIT 50';
}
*/

/*
//=======================================================================================================================
cur_frm.cscript.contact_person = function(doc, cdt, cdn){
  if (doc.contact_person) {
    arg = {};
    arg.contact_person = doc.contact_person;
    arg.customer = doc.customer;
    get_server_fields('get_contact_details',docstring(arg),'',doc,cdt,cdn,1);
  }
}
*/

/*
// hide - unhide fields based on lead or customer..
//=======================================================================================================================
cur_frm.cscript.clear_values = function(doc,cdt,cdn) {
  if(doc.enquiry_from == 'Lead') {
    doc.customer = doc.customer_name = doc.contact_person = doc.customer_group = "";
  }
  else if(doc.enquiry_from == 'Customer') {
    doc.lead =  doc.lead_name = "";
  }
  refresh_many(['lead','lead_name','customer','customer_name','contact_person','customer_group']);
}
*/

/*
//================ hide - unhide fields on basis of enquiry from either lead or customer =============================== 
cur_frm.cscript.enquiry_from = function(doc,cdt,cdn){
  cur_frm.cscript.clear_values(doc,cdt,cdn);
   doc.address = doc.territory = doc.contact_no = doc.email_id = "";
   refresh_many(['territory','address','contact_no','email_id']);
}
*/

/*
//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
  tn = createLocal('Contact');
  locals['Contact'][tn].is_customer = 1;
  if(doc.customer) locals['Contact'][tn].customer = doc.customer;
  loaddoc('Contact', tn);
}
*/

//=======================================================================================================================
cur_frm.cscript['Create New File'] = function(doc){
  var fl = LocalDB.create('File');
  fl = locals['File'][fl];
  loaddoc('File', fl.name);
}

//update follow up
//=================================================================================
cur_frm.cscript['Update Follow up'] = function(doc,cdt,cdn){

  $c_obj(make_doclist(doc.doctype, doc.name),'update_follow_up','',function(r, rt){
    refresh_field('follow_up');
    doc.__unsaved = 0;
    cur_frm.refresh_header();
  });
}

 // Create New Quotation
// =======================================================================================================================
cur_frm.cscript['Create Quotation'] = function(){
  n = createLocal("Quotation");
  $c('dt_map', args={
	  'docs':compress_doclist([locals["Quotation"][n]]),
	  'from_doctype':'Enquiry',
	  'to_doctype':'Quotation',
	  'from_docname':cur_frm.docname,
    'from_to_list':"[['Enquiry', 'Quotation'],['Enquiry Detail','Quotation Detail']]"
  }
  , function(r,rt) {
    loaddoc("Quotation", n);
    }
  );
}


// declare enquiry  lost
//-------------------------
cur_frm.cscript['Declare Enquiry Lost'] = function(){
  var e_lost_dialog;

  set_e_lost_dialog = function(){
    e_lost_dialog = new Dialog(400,150,'Add Enquiry Lost Reason');
    e_lost_dialog.make_body([
      ['HTML', 'Message', '<div class="comment">Please add enquiry lost reason</div>'],
      ['Text', 'Enquiry Lost Reason'],
      ['HTML', 'Response', '<div class = "comment" id="update_enquiry_dialog_response"></div>'],
      ['HTML', 'Add Reason', '<div></div>']
    ]);
    
    var add_reason_btn1 = $a($i(e_lost_dialog.widgets['Add Reason']), 'button', 'button');
    add_reason_btn1.innerHTML = 'Add';
    add_reason_btn1.onclick = function(){ e_lost_dialog.add(); }
    
    var add_reason_btn2 = $a($i(e_lost_dialog.widgets['Add Reason']), 'button', 'button');
    add_reason_btn2.innerHTML = 'Cancel';
    $y(add_reason_btn2,{marginLeft:'4px'});
    add_reason_btn2.onclick = function(){ e_lost_dialog.hide();}
    
    e_lost_dialog.onshow = function() {
      e_lost_dialog.widgets['Enquiry Lost Reason'].value = '';
      $i('update_enquiry_dialog_response').innerHTML = '';
    }
    
    e_lost_dialog.add = function() {
      // sending...
      $i('update_enquiry_dialog_response').innerHTML = 'Processing...';
      var arg =  strip(e_lost_dialog.widgets['Enquiry Lost Reason'].value);
      var call_back = function(r,rt) { 
        if(r.message == 'true'){
          $i('update_enquiry_dialog_response').innerHTML = 'Done';
          e_lost_dialog.hide();
        }
      }
      if(arg) {
        $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name),'declare_enquiry_lost',arg,call_back);
      }
      else{
        msgprint("Please add enquiry lost reason");
      }
      
    }
  }  
  
  if(!e_lost_dialog){
    set_e_lost_dialog();
  }  
  e_lost_dialog.show();
}

//get query select Territory
//=======================================================================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';}

/*
//===================== Enquiry From validation - either customer or lead is mandatory =====================================
cur_frm.cscript.enq_frm_validate = function(doc,cdt,cdn){
  
  if(doc.enquiry_from == 'Lead'){
    if(!doc.lead){
      alert("Lead is mandatory.");  
      validated = false; 
    }
  }
  else if(doc.enquiry_from == 'Customer'){
      if(!doc.customer){
      alert("Customer is mandatory.");
      validated = false;
    }
    else if(!doc.contact_person){
      alert("Contact Person is mandatory.");
      validated = false;
    }
    else if(!doc.customer_group){
      alert("Customer Group is mandatory.");
      validated = false;
    }
  } 
}
*/

//===================validation function ==============================================================================

cur_frm.cscript.validate = function(doc,cdt,cdn){
  //cur_frm.cscript.enq_frm_validate(doc,cdt,cdn);
}
