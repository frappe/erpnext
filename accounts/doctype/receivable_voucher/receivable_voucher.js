cur_frm.cscript.tname = "RV Detail";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

// print heading
cur_frm.pformat.print_heading = 'Invoice';

$import(Sales Common)
$import(Other Charges)
$import(SMS Control)

// On Load
// -------
cur_frm.cscript.onload = function(doc,dt,dn) {
  if(!doc.customer && doc.debit_to) get_field(dt, 'debit_to', dn).print_hide = 0;
  if (doc.__islocal) {
		if(!doc.voucher_date) set_multiple(dt,dn,{voucher_date:get_today()});
		if(!doc.due_date) set_multiple(dt,dn,{due_date:get_today()});
		if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
		
		//for previously created sales invoice, set required field related to pos
		if(doc.is_pos ==1) cur_frm.cscript.is_pos(doc, dt, dn);
	
 	    hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
  }
}

cur_frm.cscript.onload_post_render = function(doc, dt, dn) {
	if(doc.customer && doc.__islocal) {
		// called from mapper, update the account names for items and customer
		$c_obj(make_doclist(doc.doctype,doc.name),
			'load_default_accounts','',
			function(r,rt) {
				refresh_field('entries');
				refresh_field('debit_to');
			}
		);
	}
	
	if(!doc.customer && doc.__islocal) {
		// new -- load default taxes
		cur_frm.cscript.load_taxes(doc, cdt, cdn);		
	}
}


// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc, cdt, cdn) {
  if(cint(doc.is_pos) == 1)
    hide_field(['project_name', 'due_date', 'posting_time', 'sales_order_main', 'delivery_note_main', 'Get Items']);
  else
    unhide_field(['project_name', 'due_date', 'posting_time', 'sales_order_main', 'delivery_note_main', 'Get Items']);
}


// Refresh
// -------
cur_frm.cscript.refresh = function(doc, dt, dn) {

  // Show / Hide button
  cur_frm.clear_custom_buttons();
    
  if(doc.docstatus==1) { 
    cur_frm.add_custom_button('View Ledger', cur_frm.cscript['View Ledger Entry']);
    cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
    unhide_field('Repair Outstanding Amt');
    
    if(doc.is_pos==1 && doc.update_stock!=1)
      cur_frm.add_custom_button('Make Delivery', cur_frm.cscript['Make Delivery Note']);
  
    if(doc.outstanding_amount!=0)
      cur_frm.add_custom_button('Make Payment Entry', cur_frm.cscript['Make Bank Voucher']);
  }
  else  
    hide_field('Repair Outstanding Amt');
  cur_frm.cscript.is_opening(doc, dt, dn);
  cur_frm.cscript.hide_fields(doc, cdt, cdn);
}

//fetch retail transaction related fields
//--------------------------------------------
cur_frm.cscript.is_pos = function(doc,dt,dn){
  cur_frm.cscript.hide_fields(doc, cdt, cdn);
  if(doc.is_pos == 1){
    if (!doc.company) {
      msgprint("Please select company to proceed");
      doc.is_pos = 0;
      refresh_field('is_pos');
    }
    else {
      var callback = function(r,rt){
        cur_frm.refresh();
      }
      $c_obj(make_doclist(dt,dn),'set_pos_fields','',callback);
    }
  }
}


cur_frm.cscript.warehouse = function(doc, cdt , cdn) {
  var d = locals[cdt][cdn];
  if (!d.item_code) {alert("please enter item code first"); return};
  if (d.warehouse) {
    arg = "{'item_code':'" + d.item_code + "','warehouse':'" + d.warehouse +"'}";
    get_server_fields('get_actual_qty',arg,'entries',doc,cdt,cdn,1);
  }
}



//Customer
cur_frm.cscript.customer = function(doc,dt,dn) {

  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];
      get_server_fields('get_debit_to','','',doc, dt, dn, 0);
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


// Set Due Date = posting date + credit days
cur_frm.cscript.debit_to = function(doc,dt,dn) {

  var callback2 = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];
      cur_frm.refresh();
  }   
  
  var callback = function(r,rt) {
      var doc = locals[cur_frm.doctype][cur_frm.docname];    
      if(doc.customer) $c_obj(make_doclist(dt,dn), 'get_default_customer_address', '', callback2);
      if(doc.customer) unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
      cur_frm.refresh();
  }
  
  if(doc.debit_to && doc.posting_date){
    get_server_fields('get_cust_and_due_date','','',doc,dt,dn,1,callback);
  }
}



//refresh advance amount
//-------------------------------------------------

cur_frm.cscript.paid_amount = function(doc,dt,dn){
  doc.outstanding_amount = flt(doc.grand_total) - flt(doc.paid_amount) - flt(doc.write_off_amount);
  refresh_field('outstanding_amount');
}


//---- get customer details ----------------------------
cur_frm.cscript.project_name = function(doc,cdt,cdn){
	$c_obj(make_doclist(doc.doctype, doc.name),'pull_project_customer','', function(r,rt){
	  refresh_many(['customer', 'customer_name','customer_address', 'territory']);
	});
}

//Set debit and credit to zero on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
  
  cl = getchildren('RV Detail', doc.name, cur_frm.cscript.fname, doc.doctype);
  acc = '';
  cc = '';

  for(var i = 0; i<cl.length; i++) {
    
    if (cl[i].idx == 1){
      acc = cl[i].income_account;
      cc = cl[i].cost_center;
    }
    else{
      if (! cl[i].income_account) { cl[i].income_account = acc; refresh_field('income_account', cl[i].name, 'entries');}
      if (! cl[i].cost_center)  {cl[i].cost_center = cc;refresh_field('cost_center', cl[i].name, 'entries');}
    }
  }
}

cur_frm.cscript.is_opening = function(doc, dt, dn) {
  hide_field('aging_date');
  if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

/* **************************** TRIGGERS ********************************** */



// Posting Date
// ------------
//cur_frm.cscript.posting_date = cur_frm.cscript.debit_to;


// Get Items based on SO or DN Selected
cur_frm.cscript['Get Items'] = function(doc, dt, dn) {
  var callback = function(r,rt) { 
	  unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
	  cur_frm.refresh();
  }
  get_server_fields('pull_details','','',doc, dt, dn,1,callback);
}



// Allocated Amount in advances table
// -----------------------------------
cur_frm.cscript.allocated_amount = function(doc,cdt,cdn){
  cur_frm.cscript.calc_adjustment_amount(doc,cdt,cdn);
}

//Make Delivery Note Button
//-----------------------------

cur_frm.cscript['Make Delivery Note'] = function() {

  var doc = cur_frm.doc
  n = createLocal('Delivery Note');
  $c('dt_map', args={
    'docs':compress_doclist([locals['Delivery Note'][n]]),
    'from_doctype':doc.doctype,
    'to_doctype':'Delivery Note',
    'from_docname':doc.name,
    'from_to_list':"[['Receivable Voucher','Delivery Note'],['RV Detail','Delivery Note Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]"
    }, function(r,rt) {
       loaddoc('Delivery Note', n);
    }
  );
}



// Make Bank Voucher Button
// -------------------------
cur_frm.cscript['Make Bank Voucher'] = function(doc, dt, dn) {
  cur_frm.cscript.make_jv(cur_frm.doc);
}


/* ***************************** Get Query Functions ************************** */

// Debit To
// ---------
cur_frm.fields_dict.debit_to.get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

// Cash/bank account
//------------------
cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

// Write off account
//------------------
cur_frm.fields_dict.write_off_account.get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "Yes" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
  return 'SELECT `tabCost Center`.name FROM `tabCost Center` WHERE `tabCost Center`.group_or_ledger="Ledger" AND `tabCost Center`.docstatus!=2 AND `tabCost Center`.company_name="'+doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s"'
}

//project name
//--------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
  var cond = '';
  if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
  return repl('SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND %(cond)s `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}

//Territory
//-----------------------------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
}

// Income Account in Details Table
// --------------------------------
cur_frm.fields_dict.entries.grid.get_field("income_account").get_query = function(doc) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Credit" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"';
}

// warehouse in detail table
//----------------------------
cur_frm.fields_dict['entries'].grid.get_field('warehouse').get_query= function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  return "SELECT `tabBin`.`warehouse`, `tabBin`.`actual_qty` FROM `tabBin` WHERE `tabBin`.`item_code` = '"+ d.item_code +"' AND ifnull(`tabBin`.`actual_qty`,0) > 0 AND `tabBin`.`warehouse` like '%s' ORDER BY `tabBin`.`warehouse` DESC LIMIT 50";
}

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict.entries.grid.get_field("cost_center").get_query = function(doc) {
  return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.`docstatus`!= 2 ORDER BY  `tabCost Center`.`name` ASC LIMIT 50';
}

// Sales Order
// -----------
cur_frm.fields_dict.sales_order_main.get_query = function(doc) {
  if (doc.customer)
    return 'SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "' + doc.company + '" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_billed,0) < 100 and `tabSales Order`.`customer` =  "' + doc.customer + '" and `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50';
  else
    return 'SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "' + doc.company + '" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_billed,0) < 100 and `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50';
}

// Delivery Note
// --------------
cur_frm.fields_dict.delivery_note_main.get_query = function(doc) {
  if (doc.customer)	
    return 'SELECT DISTINCT `tabDelivery Note`.`name` FROM `tabDelivery Note` WHERE `tabDelivery Note`.company = "' + doc.company + '" and `tabDelivery Note`.`docstatus` = 1 and ifnull(`tabDelivery Note`.per_billed,0) < 100 and `tabDelivery Note`.`customer` =  "' + doc.customer + '" and `tabDelivery Note`.%(key)s LIKE "%s" ORDER BY `tabDelivery Note`.`name` DESC LIMIT 50';    
  else
    return 'SELECT DISTINCT `tabDelivery Note`.`name` FROM `tabDelivery Note` WHERE `tabDelivery Note`.company = "' + doc.company + '" and `tabDelivery Note`.`docstatus` = 1 and ifnull(`tabDelivery Note`.per_billed,0) < 100 and `tabDelivery Note`.%(key)s LIKE "%s" ORDER BY `tabDelivery Note`.`name` DESC LIMIT 50';        
}



cur_frm.cscript.income_account = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.income_account){
    var cl = getchildren('RV Detail', doc.name, cur_frm.cscript.fname, doc.doctype);
    for(var i = 0; i < cl.length; i++){
      if(!cl[i].income_account) cl[i].income_account = d.income_account;
    }
  }
  refresh_field(cur_frm.cscript.fname);
}


cur_frm.cscript.cost_center = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.cost_center){
    var cl = getchildren('RV Detail', doc.name, cur_frm.cscript.fname, doc.doctype);
    for(var i = 0; i < cl.length; i++){
      if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
    }
  }
  refresh_field(cur_frm.cscript.fname);
}

/* **************************************** Utility Functions *************************************** */

// Details Calculation
// --------------------
cur_frm.cscript.calc_adjustment_amount = function(doc,cdt,cdn) {
  var doc = locals[doc.doctype][doc.name];
  var el = getchildren('Advance Adjustment Detail',doc.name,'advance_adjustment_details');
  var total_adjustment_amt = 0
  for(var i in el) {
      total_adjustment_amt += flt(el[i].allocated_amount)
  }
  doc.total_advance = flt(total_adjustment_amt);
  doc.outstanding_amount = flt(doc.grand_total) - flt(total_adjustment_amt) - flt(doc.paid_amount) - flt(doc.write_off_amount);
  refresh_many(['total_advance','outstanding_amount']);
}


// Make Journal Voucher
// --------------------
cur_frm.cscript.make_jv = function(doc, dt, dn) {
  var jv = LocalDB.create('Journal Voucher');
  jv = locals['Journal Voucher'][jv];
  jv.voucher_type = 'Bank Voucher';

  jv.company = doc.company;
  jv.remark = repl('Payment received against invoice %(vn)s for %(rem)s', {vn:doc.name, rem:doc.remarks});
  jv.fiscal_year = doc.fiscal_year;
  
  // debit to creditor
  var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
  d1.account = doc.debit_to;
  d1.credit = doc.outstanding_amount;
  d1.against_invoice = doc.name;

  
  // credit to bank
  var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
  d1.debit = doc.outstanding_amount;
  
  loaddoc('Journal Voucher', jv.name);
}


/****************** Get Accounting Entry *****************/
cur_frm.cscript['View Ledger Entry'] = function(){
  var callback = function(report){
    report.set_filter('GL Entry', 'Voucher No',cur_frm.doc.name);
    report.dt.run();
  }
  loadreport('GL Entry','General Ledger', callback);
}
