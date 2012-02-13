// Module CRM

cur_frm.cscript.tname = "Sales Order Detail";
cur_frm.cscript.fname = "sales_order_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";


$import(Sales Common)
$import(Other Charges)
$import(SMS Control)


// ONLOAD
// ================================================================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
	if(!doc.transaction_date) set_multiple(cdt,cdn,{transaction_date:get_today()});
	if(!doc.price_list_currency) set_multiple(cdt, cdn, {price_list_currency: doc.currency, plc_conversion_rate: 1});
	// load default charges
	
	if(doc.__islocal){
		hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group','shipping_address']);
	}

}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		// defined in sales_common.js
		cur_frm.cscript.update_item_details(doc, cdt, cdn, callback);
	}
}

// Refresh
//==================
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.clear_custom_buttons();
	
	if(doc.docstatus==1) {
		if(doc.status != 'Stopped') {
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
			// delivery note
			if(doc.per_delivered < 100 && doc.order_type!='Maintenance')
				cur_frm.add_custom_button('Make Delivery', cur_frm.cscript['Make Delivery Note']);
			
			// maintenance
			if(doc.per_delivered < 100 && doc.order_type=='Maintenance') {
				cur_frm.add_custom_button('Make Maint. Visit', cur_frm.cscript['Make Maintenance Visit']);
				cur_frm.add_custom_button('Make Maint. Schedule', cur_frm.cscript['Make Maintenance Schedule']);
			}

			// indent
			if(doc.order_type != 'Maintenance')
				cur_frm.add_custom_button('Make ' + get_doctype_label('Indent'), cur_frm.cscript['Make Purchase Requisition']);
			
			// sales invoice
			if(doc.per_billed < 100)
				cur_frm.add_custom_button('Make Invoice', cur_frm.cscript['Make Sales Invoice']);
			
			// stop
			if(doc.per_delivered < 100 || doc.per_billed < 100)
				cur_frm.add_custom_button('Stop!', cur_frm.cscript['Stop Sales Order']);
	} else {
		
			// un-stop
			cur_frm.add_custom_button('Unstop', cur_frm.cscript['Unstop Sales Order']);
	}
		
		unhide_field(['Repair Sales Order', 'Send SMS', 'message', 'customer_mobile_no'])
	} else {
		hide_field(['Repair Sales Order', 'Send SMS', 'message', 'customer_mobile_no'])
	}
}

//customer
cur_frm.cscript.customer = function(doc,dt,dn) {
	var callback = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			get_server_fields('get_shipping_address',doc.customer,'',doc, dt, dn, 0);
			cur_frm.refresh();
	}	 

	if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', '', callback);
	if(doc.customer) unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group','shipping_address']);
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

cur_frm.cscript['Pull Quotation Details'] = function(doc,dt,dn) {
	var callback = function(r,rt){
		var doc = locals[cur_frm.doctype][cur_frm.docname];					
		if(r.message){							
			doc.quotation_no = r.message;			
			if(doc.quotation_no) {					
					unhide_field(['quotation_date','customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group','shipping_address']);									
					if(doc.customer) get_server_fields('get_shipping_address',doc.customer,'',doc, dt, dn, 0);
			}			
			cur_frm.refresh();
		}
	} 

 $c_obj(make_doclist(doc.doctype, doc.name),'pull_quotation_details','',callback);
}


//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
	tn = createLocal('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}

// DOCTYPE TRIGGERS
// ================================================================================================

/*
// ***************** get shipping address based on customer selected *****************
cur_frm.fields_dict['ship_det_no'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabShipping Address`.`name`, `tabShipping Address`.`ship_to`, `tabShipping Address`.`shipping_address` FROM `tabShipping Address` WHERE `tabShipping Address`.customer = "'+ doc.customer+'" AND `tabShipping Address`.`docstatus` != 2 AND `tabShipping Address`.`name` LIKE "%s" ORDER BY `tabShipping Address`.name ASC LIMIT 50';
}
*/


// ***************** Get project name *****************
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
	return repl('SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND %(cond)s `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}

//---- get customer details ----------------------------
cur_frm.cscript.project_name = function(doc,cdt,cdn){
	$c_obj(make_doclist(doc.doctype, doc.name),'pull_project_customer','', function(r,rt){
		refresh_many(['customer','customer_name', 'customer_address', 'contact_person', 'territory', 'contact_no', 'email_id', 'customer_group']);
	});
	
}



// *************** Customized link query for QUOTATION ***************************** 
cur_frm.fields_dict['quotation_no'].get_query = function(doc) {
	var cond='';
	if(doc.order_type) cond = ' ifnull(`tabQuotation`.order_type, "") = "'+doc.order_type+'" and';
	if(doc.customer) cond += ' ifnull(`tabQuotation`.customer, "") = "'+doc.customer+'" and';
	
	return repl('SELECT DISTINCT name, customer, transaction_date	FROM `tabQuotation` WHERE `tabQuotation`.company = "' + doc.company + '" and `tabQuotation`.`docstatus` = 1 and `tabQuotation`.status != "Order Lost" and %(cond)s `tabQuotation`.%(key)s LIKE "%s" ORDER BY `tabQuotation`.`name` DESC LIMIT 50', {cond:cond});
}


// SALES ORDER DETAILS TRIGGERS
// ================================================================================================

// ***************** Get available qty in warehouse of item selected **************** 
cur_frm.cscript.reserved_warehouse = function(doc, cdt , cdn) {
	var d = locals[cdt][cdn];
	if (d.reserved_warehouse) {
		arg = "{'item_code':'" + d.item_code + "','warehouse':'" + d.reserved_warehouse +"'}";
		get_server_fields('get_available_qty',arg,'sales_order_details',doc,cdt,cdn,1);
	}
}

//----------- make maintenance schedule----------
cur_frm.cscript['Make Maintenance Schedule'] = function() {
	var doc = cur_frm.doc;

	if (doc.docstatus == 1) { 
		$c_obj(make_doclist(doc.doctype, doc.name),'check_maintenance_schedule','',
			function(r,rt){
				if(r.message == 'No'){
					n = createLocal("Maintenance Schedule");
					$c('dt_map', args={
									'docs':compress_doclist([locals["Maintenance Schedule"][n]]),
									'from_doctype':'Sales Order',
									'to_doctype':'Maintenance Schedule',
									'from_docname':doc.name,
						'from_to_list':"[['Sales Order', 'Maintenance Schedule'], ['Sales Order Detail', 'Item Maintenance Detail']]"
					}
					, function(r,rt) {
						loaddoc("Maintenance Schedule", n);
					}
					);
				}
				else{
					msgprint("You have already created Maintenance Schedule against this Sales Order");
				}
			}
		);
	}
}

//------------ make maintenance visit ------------
cur_frm.cscript['Make Maintenance Visit'] = function() {
	var doc = cur_frm.doc;

	if (doc.docstatus == 1) { 
		$c_obj(make_doclist(doc.doctype, doc.name),'check_maintenance_visit','',
			function(r,rt){
				if(r.message == 'No'){
					n = createLocal("Maintenance Visit");
					$c('dt_map', args={
									'docs':compress_doclist([locals["Maintenance Visit"][n]]),
									'from_doctype':'Sales Order',
									'to_doctype':'Maintenance Visit',
									'from_docname':doc.name,
						'from_to_list':"[['Sales Order', 'Maintenance Visit'], ['Sales Order Detail', 'Maintenance Visit Detail']]"
					}
					, function(r,rt) {
						loaddoc("Maintenance Visit", n);
					}
					);
				}
				else{
					msgprint("You have already completed maintenance against this Sales Order");
				}
			}
		);
	}
}

// make indent
// ================================================================================================
cur_frm.cscript['Make Purchase Requisition'] = function() {
	var doc = cur_frm.doc;
	if (doc.docstatus == 1) { 
	n = createLocal("Indent");
	$c('dt_map', args={
					'docs':compress_doclist([locals["Indent"][n]]),
					'from_doctype':'Sales Order',
					'to_doctype':'Indent',
					'from_docname':doc.name,
		'from_to_list':"[['Sales Order', 'Indent'], ['Sales Order Detail', 'Indent Detail']]"
	}
	, function(r,rt) {
		loaddoc("Indent", n);
		}
		);
	}
}


// MAKE DELIVERY NOTE
// ================================================================================================
cur_frm.cscript['Make Delivery Note'] = function() {
	var doc = cur_frm.doc;
	if (doc.docstatus == 1) { 
	n = createLocal("Delivery Note");
	$c('dt_map', args={
					'docs':compress_doclist([locals["Delivery Note"][n]]),
					'from_doctype':'Sales Order',
					'to_doctype':'Delivery Note',
					'from_docname':doc.name,
		'from_to_list':"[['Sales Order', 'Delivery Note'], ['Sales Order Detail', 'Delivery Note Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]"
	}
	, function(r,rt) {
		loaddoc("Delivery Note", n);
		}
		);
	}
}


// MAKE SALES INVOICE
// ================================================================================================
cur_frm.cscript['Make Sales Invoice'] = function() {
	var doc = cur_frm.doc;

	n = createLocal('Receivable Voucher');
	$c('dt_map', args={
		'docs':compress_doclist([locals['Receivable Voucher'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Receivable Voucher',
		'from_docname':doc.name,
		'from_to_list':"[['Sales Order','Receivable Voucher'],['Sales Order Detail','RV Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]"
		}, function(r,rt) {
			 loaddoc('Receivable Voucher', n);
		}
	);
}


// STOP SALES ORDER
// ==================================================================================================
cur_frm.cscript['Stop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm("Are you sure you want to STOP " + doc.name);

	if (check) {
		$c('runserverobj', args={'method':'stop_sales_order', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

// UNSTOP SALES ORDER
// ==================================================================================================
cur_frm.cscript['Unstop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm("Are you sure you want to UNSTOP " + doc.name);

	if (check) {
		$c('runserverobj', args={'method':'unstop_sales_order', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

//get query select Territory
//=======================================================================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

$import(Notification Control)
cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	var args = {
		type: 'Sales Order',
		doctype: 'Sales Order'
	}
	cur_frm.cscript.notify(doc, args);
}
