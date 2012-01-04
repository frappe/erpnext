// Module CRM
cur_frm.cscript.tname = "Quotation Detail";
cur_frm.cscript.fname = "quotation_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

// =====================================================================================
$import(Sales Common)
$import(Other Charges)
$import(SMS Control)

// ONLOAD
// ===================================================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  if(!doc.quotation_to) hide_field(['customer','customer_address','contact_person','customer_name','lead', 'lead_name', 'address_display', 'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']);
  if(!doc.price_list_name) set_multiple(cdt,cdn,{price_list_name:sys_defaults.price_list_name});
  if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
  if(!doc.transaction_date) set_multiple(cdt,cdn,{transaction_date:get_today()});
  if(!doc.conversion_rate) set_multiple(cdt,cdn,{conversion_rate:'1.00'});
  if(!doc.currency && sys_defaults.currency) set_multiple(cdt,cdn,{currency:sys_defaults.currency});
  if(!doc.price_list_currency) set_multiple(cdt, cdn, {price_list_currency: doc.currency, plc_conversion_rate: 1});

  if(!doc.company && sys_defaults.company) set_multiple(cdt,cdn,{company:sys_defaults.company});
  if(!doc.fiscal_year && sys_defaults.fiscal_year) set_multiple(cdt,cdn,{fiscal_year:sys_defaults.fiscal_year});

  if(doc.quotation_to) {
    if(doc.quotation_to == 'Customer') {
      hide_field(['lead', 'lead_name']);
    }
    else if (doc.quotation_to == 'Lead') {
      hide_field(['customer','customer_address','contact_person', 'customer_name','contact_display', 'customer_group']);
    }
  }
}

cur_frm.cscript.onload_post_render = function(doc, dt, dn) {
  // load default charges
  if(doc.__islocal && !getchildren('RV Tax Detail', doc.name, 'other_charges', doc.doctype).length)
    cur_frm.cscript.load_taxes(doc, cdt, cdn);
}

// hide - unhide fields based on lead or customer..
// =======================================================================================================================
cur_frm.cscript.lead_cust_show = function(doc,cdt,cdn){
  if(doc.quotation_to == 'Lead'){
    unhide_field(['lead']);
    hide_field(['lead_name','customer','customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
    doc.lead = doc.lead_name = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
  }
  else if(doc.quotation_to == 'Customer'){
    unhide_field(['customer']);
    hide_field(['lead','lead_name','address_display','contact_display','contact_mobile','contact_email','territory']);
    doc.lead = doc.lead_name = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
  }
}



//================ hide - unhide fields on basis of quotation to either lead or customer ===============================
cur_frm.cscript.quotation_to = function(doc,cdt,cdn){
  cur_frm.cscript.lead_cust_show(doc,cdt,cdn);
}


// REFRESH
// ===================================================================================
cur_frm.cscript.refresh = function(doc, cdt, cdn) {

  cur_frm.clear_custom_buttons();

  if(doc.docstatus == 1 && doc.status!='Order Lost') {
    cur_frm.add_custom_button('Make Sales Order', cur_frm.cscript['Make Sales Order']);
    cur_frm.add_custom_button('Set as Lost', cur_frm.cscript['Declare Order Lost']);
    cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
  }

  if (!doc.docstatus) hide_field(['Update Follow up']);
  else unhide_field(['Update Follow up']);
}


//customer
cur_frm.cscript.customer = function(doc,dt,dn) {
  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];
      cur_frm.refresh();
  }

  if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', '', callback);
  if(doc.customer) unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
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

//lead
cur_frm.fields_dict['lead'].get_query = function(doc,cdt,cdn){
  return 'SELECT `tabLead`.name, `tabLead`.lead_name FROM `tabLead` WHERE `tabLead`.%(key)s LIKE "%s"  ORDER BY  `tabLead`.`name` ASC LIMIT 50';
}

cur_frm.cscript.lead = function(doc, cdt, cdn) {
  if(doc.lead) get_server_fields('get_lead_details', doc.lead,'', doc, cdt, cdn, 1);
  if(doc.lead) unhide_field(['lead_name','address_display','contact_mobile','contact_email','territory']);
}


// =====================================================================================
cur_frm.fields_dict['enq_no'].get_query = function(doc,cdt,cdn){
  var cond='';
  var cond1='';
  if(doc.order_type) cond = 'ifnull(`tabEnquiry`.enquiry_type, "") = "'+doc.order_type+'" AND';
  if(doc.customer) cond1 = '`tabEnquiry`.customer = "'+doc.customer+'" AND';
  else if(doc.lead) cond1 = '`tabEnquiry`.lead = "'+doc.lead+'" AND';

  return repl('SELECT `tabEnquiry`.`name` FROM `tabEnquiry` WHERE `tabEnquiry`.`docstatus` = 1 AND `tabEnquiry`.status = "Submitted" AND %(cond)s %(cond1)s `tabEnquiry`.`name` LIKE "%s" ORDER BY `tabEnquiry`.`name` ASC LIMIT 50', {cond:cond, cond1:cond1});
}

// Make Sales Order
// =====================================================================================
cur_frm.cscript['Make Sales Order'] = function() {
  var doc = cur_frm.doc;

  if (doc.docstatus == 1) {
    var n = createLocal("Sales Order");
    $c('dt_map', args={
      'docs':compress_doclist([locals["Sales Order"][n]]),
      'from_doctype':'Quotation',
      'to_doctype':'Sales Order',
      'from_docname':doc.name,
      'from_to_list':"[['Quotation', 'Sales Order'], ['Quotation Detail', 'Sales Order Detail'],['RV Tax Detail','RV Tax Detail'], ['Sales Team', 'Sales Team'], ['TC Detail', 'TC Detail']]"
    }, function(r,rt) {
      loaddoc("Sales Order", n);
    });
  }
}

//pull enquiry details
cur_frm.cscript['Pull Enquiry Detail'] = function(doc,cdt,cdn){

  var callback = function(r,rt){
    if(r.message){
      doc.quotation_to = r.message;

		  if(doc.quotation_to == 'Lead') {
  			  unhide_field(['lead','lead_name','address_display','contact_mobile','contact_email','territory']);
		  }
		  else if(doc.quotation_to == 'Customer') {
			  unhide_field(['customer','customer_address','contact_person','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
		  }
		  refresh_many(['quotation_details','quotation_to','customer','customer_address','contact_person','lead','lead_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group','order_type']);
    }
  }

  $c_obj(make_doclist(doc.doctype, doc.name),'pull_enq_details','',callback);

}

//update follow up
//=================================================================================
cur_frm.cscript['Update Follow up'] = function(doc){

  $c_obj(make_doclist(doc.doctype, doc.name),'update_followup_details','',function(r, rt){
    refresh_field('follow_up');
    doc.__unsaved = 0;
    cur_frm.refresh_header();
  });
}


// declare order lost
//-------------------------
cur_frm.cscript['Declare Order Lost'] = function(){
  var qtn_lost_dialog;

  set_qtn_lost_dialog = function(doc,cdt,cdn){
    qtn_lost_dialog = new Dialog(400,400,'Add Quotation Lost Reason');
    qtn_lost_dialog.make_body([
      ['HTML', 'Message', '<div class="comment">Please add quotation lost reason</div>'],
      ['Text', 'Quotation Lost Reason'],
      ['HTML', 'Response', '<div class = "comment" id="update_quotation_dialog_response"></div>'],
      ['HTML', 'Add Reason', '<div></div>']
    ]);

    var add_reason_btn1 = $a($i(qtn_lost_dialog.widgets['Add Reason']), 'button', 'button');
    add_reason_btn1.innerHTML = 'Add';
    add_reason_btn1.onclick = function(){ qtn_lost_dialog.add(); }

    var add_reason_btn2 = $a($i(qtn_lost_dialog.widgets['Add Reason']), 'button', 'button');
    add_reason_btn2.innerHTML = 'Cancel';
    $y(add_reason_btn2,{marginLeft:'4px'});
    add_reason_btn2.onclick = function(){ qtn_lost_dialog.hide();}

    qtn_lost_dialog.onshow = function() {
      qtn_lost_dialog.widgets['Quotation Lost Reason'].value = '';
      $i('update_quotation_dialog_response').innerHTML = '';
    }

    qtn_lost_dialog.add = function() {
      // sending...
      $i('update_quotation_dialog_response').innerHTML = 'Processing...';
      var arg =  strip(qtn_lost_dialog.widgets['Quotation Lost Reason'].value);
      var call_back = function(r,rt) {
        if(r.message == 'true'){
          $i('update_quotation_dialog_response').innerHTML = 'Done';
          qtn_lost_dialog.hide();
        }
      }
      if(arg) $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name),'declare_order_lost',arg,call_back);
      else msgprint("Please add Quotation lost reason");
    }
  }

  if(!qtn_lost_dialog){
    set_qtn_lost_dialog(doc,cdt,cdn);
  }
  qtn_lost_dialog.show();
}


// GET REPORT
// ========================================================================================
cur_frm.cscript['Get Report'] = function(doc,cdt,cdn) {
  var callback = function(report){
  report.set_filter('Sales Order Detail', 'Quotation No.',doc.name)
  report.dt.run();
 }
 loadreport('Sales Order Detail','Itemwise Sales Details', callback);
}


//===================== Quotation to validation - either customer or lead mandatory ====================
cur_frm.cscript.quot_to_validate = function(doc,cdt,cdn){

  if(doc.quotation_to == 'Lead'){

    if(!doc.lead){
      alert("Lead is mandatory.");
      validated = false;
    }
  }
  else if(doc.quotation_to == 'Customer'){
    if(!doc.customer){
      alert("Customer is mandatory.");
      validated = false;
    }
  }
}

//===================validation function =================================

cur_frm.cscript.validate = function(doc,cdt,cdn){
  cur_frm.cscript.quot_to_validate(doc,cdt,cdn);
}

//================ Last Quoted Price and Last Sold Price suggestion ======================
cur_frm.fields_dict['quotation_details'].grid.get_field('item_code').get_query= function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  var cond = (doc.order_type == 'Maintenance')? " and tabItem.is_service_item = 'Yes'" : " and tabItem.is_sales_item = 'Yes'"
  if(doc.customer)
    return repl("SELECT i.name,i.item_code,concat('Last quoted at - ',cast(quote_rate as char)) as quote_rate,concat('Last sold at - ',cast(sales_rate as char)) as sales_rate, i.item_name, i.description FROM\
		(\
			select item_code,name, item_name, description from tabItem where tabItem.%(key)s like '%s' %(cond)s\
		)i\
		left join\
		(\
			select q.item_code,q.quote_rate from\
			(\
				select q.transaction_date,qd.item_code,basic_rate as quote_rate from `tabQuotation Detail` qd, `tabQuotation` q where q.name=qd.parent and q.docstatus=1 and customer='%(cust)s'\
			)q,\
			(\
				select qd.item_code,max(transaction_date) as transaction_date from `tabQuotation Detail` qd, `tabQuotation` q where q.name=qd.parent and q.docstatus=1 and customer='%(cust)s' group by qd.item_code\
			)m where q.item_code=m.item_code and q.transaction_date=m.transaction_date\
		)q on i.item_code=q.item_code\
		left join\
		(\
			select r.item_code,r.sales_rate from\
			(\
				select r.voucher_date,rd.item_code,basic_rate as sales_rate from `tabRV Detail` rd, `tabReceivable Voucher` r where r.name=rd.parent and r.docstatus=1 and customer='%(cust)s'\
			)r,\
			(\
				select rd.item_code,max(voucher_date) as voucher_date from `tabRV Detail` rd, `tabReceivable Voucher` r where r.name=rd.parent and r.docstatus=1 and customer='%(cust)s' group by rd.item_code\
			)m where r.item_code=m.item_code and r.voucher_date=m.voucher_date\
		)s on i.item_code=s.item_code ORDER BY item_code LIMIT 50",{cust:doc.customer, cond:cond});
  else
    return repl("SELECT name, item_name, description FROM tabItem WHERE `tabItem`.%(key)s LIKE '%s' %(cond)s ORDER BY tabItem.item_code DESC LIMIT 50", {cond:cond});
}

$import(Notification Control)
cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	var args = {
		type: 'Quotation',
		doctype: 'Quotation'
	}
	cur_frm.cscript.notify(doc, args);
}
