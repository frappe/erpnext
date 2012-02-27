// Module Material Management
cur_frm.cscript.tname = "Delivery Note Detail";
cur_frm.cscript.fname = "delivery_note_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

$import(Sales Common)
$import(Other Charges)
$import(SMS Control)

// ONLOAD
// ================================================================================================
cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
	if(!doc.transaction_date) set_multiple(dt,dn,{transaction_date:get_today()});
	if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
	if(doc.__islocal && doc.customer) cur_frm.cscript.pull_item_details_onload(doc,dt,dn);
	if(!doc.price_list_currency) {
		set_multiple(dt, dn, {price_list_currency: doc.currency, plc_conversion_rate:1});
	}
	if(!doc.posting_time) doc.posting_time = wn.datetime.get_cur_time()
		
	if(doc.__islocal){
		hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
	}	
}

cur_frm.cscript.onload_post_render = function(doc, dt, dn) {
	// defined in sales_common.js
	if(doc.__islocal) cur_frm.cscript.update_item_details(doc, dt, dn);
} 

// REFRESH
// ================================================================================================
cur_frm.cscript.refresh = function(doc, cdt, cdn) { 
	cur_frm.clear_custom_buttons();
	var callback = function() {
		cur_frm.cscript.dynamic_label(doc, cdt, cdn);
	}
	cur_frm.cscript.hide_price_list_currency(doc, cdt, cdn, callback); 

 
	if(doc.per_billed < 100 && doc.docstatus==1) cur_frm.add_custom_button('Make Invoice', cur_frm.cscript['Make Sales Invoice']);
	
	if(doc.per_installed < 100 && doc.docstatus==1) cur_frm.add_custom_button('Make Installation Note', cur_frm.cscript['Make Installation Note']);

	if (doc.docstatus!=1) {
		hide_field(['SMS', 'Send SMS', 'message', 'customer_mobile_no', 'Repair Delivery Note']);
	} else {
		cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
		unhide_field(['SMS','Send SMS', 'message', 'customer_mobile_no', 'Repair Delivery Note']);
	}

	if(doc.docstatus==1) {
		cur_frm.add_custom_button('Make Packing Slip', cur_frm.cscript['Make Packing Slip']);
	}
	
	set_print_hide(doc, cdt, cdn);
}


//customer
cur_frm.cscript.customer = function(doc,dt,dn,onload) {	
	var callback = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			cur_frm.refresh();
	} 
	var args = onload ? 'onload':''
	if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_shipping_address', args, callback);
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

cur_frm.cscript['Get Items'] = function(doc,dt,dn) {
	var callback = function(r,rt){
		var doc = locals[cur_frm.doctype][cur_frm.docname];					
		if(r.message){							
			doc.sales_order_no = r.message;			
			if(doc.sales_order_no) {					
					unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);														
			}			
			refresh_many(['delivery_note_details','customer','customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
		}
	} 
 $c_obj(make_doclist(doc.doctype, doc.name),'pull_sales_order_details','',callback); 
}


//RV-DN : Pull Item details - UOM, Item Group as it was not in Sales Invoice
//---------------------------------------------------------------------
cur_frm.cscript.pull_item_details_onload = function(doc,dt,dn){
	var callback = function(r,rt){
		refresh_field('delivery_note_details');
		cur_frm.cscript.customer(doc,dt,dn,onload=true);
	} 
	$c_obj(make_doclist(dt,dn),'set_item_details','',callback);
}

//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
	tn = createLocal('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}

//========================= Overloaded query for link batch_no =============================================================
cur_frm.fields_dict['delivery_note_details'].grid.get_field('batch_no').get_query= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.item_code){
		return "SELECT tabBatch.name, tabBatch.description FROM tabBatch WHERE tabBatch.docstatus != 2 AND tabBatch.item = '"+ d.item_code +"' AND `tabBatch`.`name` like '%s' ORDER BY `tabBatch`.`name` DESC LIMIT 50"
	}
	else{
		alert("Please enter Item Code.");
	}
}

// ***************** Get project name *****************
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
	return repl('SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND %(cond)s `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}


// *************** Customized link query for SALES ORDER based on customer and currency***************************** 
cur_frm.fields_dict['sales_order_no'].get_query = function(doc) {
	doc = locals[this.doctype][this.docname];
	var cond = '';
	
	if(doc.customer) {
		if(doc.currency) cond = '`tabSales Order`.customer = "'+doc.customer+'" and `tabSales Order`.currency = "'+doc.currency+'" and';
		else cond = '`tabSales Order`.customer = "'+doc.customer+'" and';
	}
	else {
		if(doc.currency) cond = '`tabSales Order`.currency = "'+doc.currency+'" and';
		else cond = '';
	}
	if(doc.project_name){
		cond += '`tabSales Order`.project_name ="'+doc.project_name+'"';
	}
	return repl('SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "%(company)s" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_delivered,0) < 100 and %(cond)s `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50', {company:doc.company,cond:cond})
}


// ****************************** DELIVERY TYPE ************************************
cur_frm.cscript.delivery_type = function(doc, cdt, cdn) {
	if (doc.delivery_type = 'Sample') cfn_set_fields(doc, cdt, cdn);
}

cur_frm.cscript.serial_no = function(doc, cdt , cdn) {
	var d = locals[cdt][cdn];
	if (d.serial_no) {
		 get_server_fields('get_serial_details',d.serial_no,'delivery_note_details',doc,cdt,cdn,1);
	}
}


cur_frm.cscript.warehouse = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (! d.item_code) {alert("please enter item code first"); return};
	if (d.warehouse) {
		arg = "{'item_code':'" + d.item_code + "','warehouse':'" + d.warehouse +"'}";
		get_server_fields('get_actual_qty',arg,'delivery_note_details',doc,cdt,cdn,1);
	}
}


cur_frm.fields_dict['transporter_name'].get_query = function(doc) {
	return 'SELECT DISTINCT `tabSupplier`.`name` FROM `tabSupplier` WHERE `tabSupplier`.supplier_type = "transporter" AND `tabSupplier`.docstatus != 2 AND `tabSupplier`.%(key)s LIKE "%s" ORDER BY `tabSupplier`.`name` LIMIT 50';
}

//-----------------------------------Make Sales Invoice----------------------------------------------
cur_frm.cscript['Make Sales Invoice'] = function() {
	var doc = cur_frm.doc
	n = createLocal('Receivable Voucher');
	$c('dt_map', args={
		'docs':compress_doclist([locals['Receivable Voucher'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Receivable Voucher',
		'from_docname':doc.name,
		'from_to_list':"[['Delivery Note','Receivable Voucher'],['Delivery Note Detail','RV Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]"
		}, function(r,rt) {
			 loaddoc('Receivable Voucher', n);
		}
	);
}

//-----------------------------------Make Installation Note----------------------------------------------
cur_frm.cscript['Make Installation Note'] = function() {
	var doc = cur_frm.doc;
	if(doc.per_installed < 100){
		n = createLocal('Installation Note');
		$c('dt_map', args={
			'docs':compress_doclist([locals['Installation Note'][n]]),
			'from_doctype':doc.doctype,
			'to_doctype':'Installation Note',
			'from_docname':doc.name,
			'from_to_list':"[['Delivery Note','Installation Note'],['Delivery Note Detail','Installed Item Details']]"
			}, function(r,rt) {
				 loaddoc('Installation Note', n);
			}
		);
	}
	else if(doc.per_installed >= 100)
		msgprint("Item installation is already completed")
}

//-----------------------------------Make Sales Invoice----------------------------------------------
cur_frm.cscript['Make Packing Slip'] = function() {
	var doc = cur_frm.doc
	n = createLocal('Packing Slip');
	$c('dt_map', args={
		'docs':compress_doclist([locals['Packing Slip'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Packing Slip',
		'from_docname':doc.name,
		'from_to_list':"[['Delivery Note','Packing Slip'],['Delivery Note Detail','Packing Slip Detail']]"
		}, function(r,rt) {
			 loaddoc('Packing Slip', n);
		}
	);
}


//get query select Territory
//=======================================================================================================================
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

//------------------------for printing without amount----------

var set_print_hide= function(doc, cdt, cdn){
	if (doc.print_without_amount) {
		fields['Delivery Note']['currency'].print_hide = 1;
		fields['Delivery Note Detail']['export_rate'].print_hide = 1;
		fields['Delivery Note Detail']['adj_rate'].print_hide = 1;
		fields['Delivery Note Detail']['ref_rate'].print_hide = 1;
		fields['Delivery Note Detail']['export_amount'].print_hide = 1;
	} else {
		fields['Delivery Note']['currency'].print_hide = 0;
		fields['Delivery Note Detail']['export_rate'].print_hide = 0;
		fields['Delivery Note Detail']['adj_rate'].print_hide = 0;
		fields['Delivery Note Detail']['ref_rate'].print_hide = 0;
		fields['Delivery Note Detail']['export_amount'].print_hide = 0;
	}
}

cur_frm.cscript.print_without_amount = function(doc, cdt, cdn) {
	set_print_hide(doc, cdt, cdn);
}


//****************** For print sales order no and date*************************
cur_frm.pformat.sales_order_no= function(doc, cdt, cdn){
	//function to make row of table
	
	var make_row = function(title,val1, val2, bold){
		var bstart = '<b>'; var bend = '</b>';

		return '<tr><td style="width:39%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
		 +'<td style="width:61%;text-align:left;">'+val1+(val2?' ('+dateutil.str_to_user(val2)+')':'')+'</td>'
		 +'</tr>'
	}

	out ='';
	
	var cl = getchildren('Delivery Note Detail',doc.name,'delivery_note_details');

	// outer table	
	var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 50%"></td><td>';
	
	// main table
	out +='<table class="noborder" style="width:100%">';

	// add rows
	if(cl.length){
		prevdoc_list = new Array();
		for(var i=0;i<cl.length;i++){
			if(cl[i].prevdoc_doctype == 'Sales Order' && cl[i].prevdoc_docname && prevdoc_list.indexOf(cl[i].prevdoc_docname) == -1) {
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

$import(Notification Control)
cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	var args = {
		type: 'Delivery Note',
		doctype: 'Delivery Note'
	}
	cur_frm.cscript.notify(doc, args);
}
