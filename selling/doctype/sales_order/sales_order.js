// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// Module CRM

cur_frm.cscript.tname = "Sales Order Item";
cur_frm.cscript.fname = "sales_order_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";


wn.require('app/selling/doctype/sales_common/sales_common.js');
wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');


cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.cscript.manage_rounded_total();
	
	if(!doc.status) set_multiple(cdt,cdn,{status:'Draft'});
	if(!doc.transaction_date) set_multiple(cdt,cdn,{transaction_date:get_today()});
	if(!doc.price_list_currency) set_multiple(cdt, cdn, {price_list_currency: doc.currency, plc_conversion_rate: 1});
	// load default charges
	
	if(doc.__islocal && !doc.customer){
		hide_field(['customer_address','contact_person', 'customer_name', 
			'address_display', 'contact_display', 'contact_mobile', 
			'contact_email', 'territory',  'customer_group']);
	}
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	var callback = function(doc, cdt, cdn) {
		if(doc.__islocal) {
			// defined in sales_common.js
			cur_frm.cscript.update_item_details(doc, cdt, cdn);
		}
	}
	
	cur_frm.cscript.hide_price_list_currency(doc, cdt, cdn, callback); 

}


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.clear_custom_buttons();
	erpnext.hide_naming_series();

	if (!cur_frm.cscript.is_onload) cur_frm.cscript.hide_price_list_currency(doc, cdt, cdn); 
	
	cur_frm.toggle_display("contact_info", doc.customer);
	
	if(doc.docstatus==1) {
		if(doc.status != 'Stopped') {
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);
			// delivery note
			if(flt(doc.per_delivered, 2) < 100 && doc.order_type=='Sales')
				cur_frm.add_custom_button('Make Delivery', cur_frm.cscript['Make Delivery Note']);
			
			// maintenance
			if(flt(doc.per_delivered, 2) < 100 && (doc.order_type !='Sales')) {
				cur_frm.add_custom_button('Make Maint. Visit', cur_frm.cscript.make_maintenance_visit);
				cur_frm.add_custom_button('Make Maint. Schedule', cur_frm.cscript['Make Maintenance Schedule']);
			}

			// indent
			if(!doc.order_type || (doc.order_type == 'Sales'))
				cur_frm.add_custom_button('Make ' + wn._('Material Request'), cur_frm.cscript['Make Material Request']);
			
			// sales invoice
			if(flt(doc.per_billed, 2) < 100)
				cur_frm.add_custom_button('Make Invoice', cur_frm.cscript['Make Sales Invoice']);
			
			// stop
			if(flt(doc.per_delivered, 2) < 100 || doc.per_billed < 100)
				cur_frm.add_custom_button('Stop!', cur_frm.cscript['Stop Sales Order']);
		} else {	
			// un-stop
			cur_frm.add_custom_button('Unstop', cur_frm.cscript['Unstop Sales Order']);
		}
	}
	
	cur_frm.cscript.order_type(doc);
}

cur_frm.cscript.order_type = function(doc) {
	if(doc.order_type == "Sales") {
		cur_frm.toggle_reqd("delivery_date", 1);
	} else {
		cur_frm.toggle_reqd("delivery_date", 0);
	}
}

//customer
cur_frm.cscript.customer = function(doc,dt,dn) {
	cur_frm.toggle_display("contact_info", doc.customer);
	
	var pl = doc.price_list_name;
	var callback = function(r,rt) {
		var callback2  = function(r, rt) {
			if(doc.customer) 
				unhide_field(['customer_address', 'contact_person', 'territory','customer_group']);
			cur_frm.refresh();
			
			if(!onload && (pl != doc.price_list_name)) cur_frm.cscript.price_list_name(doc, dt, dn);

		}
		var doc = locals[cur_frm.doctype][cur_frm.docname];
		get_server_fields('get_shipping_address',doc.customer,'',doc, dt, dn, 0, callback2);
			
	}	 
	if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 
		'get_default_customer_address', '', callback);
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict.shipping_address_name.get_query = cur_frm.fields_dict['customer_address'].get_query;

cur_frm.cscript.shipping_address_name = function() {
	if(cur_frm.doc.shipping_address_name) {
		wn.model.with_doc("Address", cur_frm.doc.shipping_address_name, function(name) {
			var address = wn.model.get_doc("Address", name);
			
			var out = $.map(["address_line1", "address_line2", "city"], 
				function(f) { return address[f]; });

			var state_pincode = $.map(["state", "pincode"], function(f) { return address[f]; }).join(" ");
			if(state_pincode) out.push(state_pincode);
			
			if(address["country"]) out.push(address["country"]);
			
			out.concat($.map([["Phone:", address["phone"]], ["Fax:", address["fax"]]], 
				function(val) { return val[1] ? val.join(" ") : null; }));
			
			cur_frm.set_value("shipping_address", out.join("\n"));
		});
	}
};

cur_frm.cscript.pull_quotation_details = function(doc,dt,dn) {
	var callback = function(r,rt){
		var doc = locals[cur_frm.doctype][cur_frm.docname];					
		if(!r.exc){							
			doc.quotation_no = r.message;			
			if(doc.quotation_no) {					
				unhide_field(['quotation_date', 'customer_address', 
					'contact_person', 'territory', 'customer_group']);
				if(doc.customer) get_server_fields('get_shipping_address', doc.customer, '', doc, dt, dn, 0);
			}			
			cur_frm.refresh_fields();
		}
	} 

 $c_obj(make_doclist(doc.doctype, doc.name),'pull_quotation_details','',callback);
}


cur_frm.cscript.new_contact = function(){
	tn = wn.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}

cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
	return repl('SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND %(cond)s `tabProject`.name LIKE "%s" \
		ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}


cur_frm.fields_dict['quotation_no'].get_query = function(doc) {
	var cond='';
	if(doc.order_type) cond = ' ifnull(`tabQuotation`.order_type, "") = "'
		+doc.order_type+'" and';
	if(doc.customer) cond += ' ifnull(`tabQuotation`.customer, "") = "'
		+doc.customer+'" and';
	
	return repl('SELECT DISTINCT name, customer, transaction_date FROM `tabQuotation` \
		WHERE `tabQuotation`.company = "' 
		+ doc.company + '" and `tabQuotation`.`docstatus` = 1 \
			and `tabQuotation`.status != "Order Lost" \
			and %(cond)s `tabQuotation`.%(key)s LIKE "%s" \
			ORDER BY `tabQuotation`.`name` DESC LIMIT 50', {cond:cond});
}


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
					n = wn.model.make_new_doc_and_get_name("Maintenance Schedule");
					$c('dt_map', args={
									'docs':wn.model.compress([locals["Maintenance Schedule"][n]]),
									'from_doctype':'Sales Order',
									'to_doctype':'Maintenance Schedule',
									'from_docname':doc.name,
						'from_to_list':"[['Sales Order', 'Maintenance Schedule'], ['Sales Order Item', 'Maintenance Schedule Item']]"
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

cur_frm.cscript.make_maintenance_visit = function() {
	var doc = cur_frm.doc;

	if (doc.docstatus == 1) { 
		$c_obj(make_doclist(doc.doctype, doc.name),'check_maintenance_visit','',
			function(r,rt){
				if(r.message == 'No'){
					n = wn.model.make_new_doc_and_get_name("Maintenance Visit");
					$c('dt_map', args={
									'docs':wn.model.compress([locals["Maintenance Visit"][n]]),
									'from_doctype':'Sales Order',
									'to_doctype':'Maintenance Visit',
									'from_docname':doc.name,
						'from_to_list':"[['Sales Order', 'Maintenance Visit'], ['Sales Order Item', 'Maintenance Visit Purpose']]"
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

cur_frm.cscript['Make Material Request'] = function() {
	var doc = cur_frm.doc;
	if (doc.docstatus == 1) { 
	n = wn.model.make_new_doc_and_get_name("Material Request");
	$c('dt_map', args={
					'docs':wn.model.compress([locals["Material Request"][n]]),
					'from_doctype':'Sales Order',
					'to_doctype':'Material Request',
					'from_docname':doc.name,
		'from_to_list':"[['Sales Order', 'Material Request'], ['Sales Order Item', 'Material Request Item']]"
	}
	, function(r,rt) {
		loaddoc("Material Request", n);
		}
		);
	}
}


cur_frm.cscript['Make Delivery Note'] = function() {
	var doc = cur_frm.doc;
	if (doc.docstatus == 1) { 
	n = wn.model.make_new_doc_and_get_name("Delivery Note");
	$c('dt_map', args={
					'docs':wn.model.compress([locals["Delivery Note"][n]]),
					'from_doctype':'Sales Order',
					'to_doctype':'Delivery Note',
					'from_docname':doc.name,
		'from_to_list':"[['Sales Order', 'Delivery Note'], ['Sales Order Item', 'Delivery Note Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]"
	}
	, function(r,rt) {
		loaddoc("Delivery Note", n);
		}
		);
	}
}


cur_frm.cscript['Make Sales Invoice'] = function() {
	var doc = cur_frm.doc;

	n = wn.model.make_new_doc_and_get_name('Sales Invoice');
	$c('dt_map', args={
		'docs':wn.model.compress([locals['Sales Invoice'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Sales Invoice',
		'from_docname':doc.name,
		'from_to_list':"[['Sales Order','Sales Invoice'],['Sales Order Item','Sales Invoice Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]"
		}, function(r,rt) {
			 loaddoc('Sales Invoice', n);
		}
	);
}


cur_frm.cscript['Stop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm("Are you sure you want to STOP " + doc.name);

	if (check) {
		$c('runserverobj', {
			'method':'stop_sales_order', 
			'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))
			}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

cur_frm.cscript['Unstop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm("Are you sure you want to UNSTOP " + doc.name);

	if (check) {
		$c('runserverobj', {
			'method':'unstop_sales_order', 
			'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))
		}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.sales_order)) {
		cur_frm.email_doc(wn.boot.notification_settings.sales_order_message);
	}
};