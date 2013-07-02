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

wn.require('app/utilities/doctype/sms_control/sms_control.js');

cur_frm.cscript.refresh = function(doc, cdt, cdn){
	erpnext.hide_naming_series();
	
	cur_frm.clear_custom_buttons();
	if(doc.docstatus == 1) {
		cur_frm.add_custom_button('Create Quotation', cur_frm.cscript['Create Quotation']);
		cur_frm.add_custom_button('Opportunity Lost', cur_frm.cscript['Declare Opportunity Lost']);
		cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);
	}
	
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	
}

// ONLOAD
// ===============================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {

	if(!doc.enquiry_from && doc.customer)
		doc.enquiry_from = "Customer";
	if(!doc.enquiry_from && doc.lead)
		doc.enquiry_from = "Lead";

	if(!doc.enquiry_from) 
		hide_field(['customer', 'customer_address', 'contact_person', 'customer_name','lead', 'address_display', 'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']);
	if(!doc.status) 
		set_multiple(cdt,cdn,{status:'Draft'});
	if(!doc.date) 
		doc.transaction_date = date.obj_to_str(new Date());
	if(!doc.company && sys_defaults.company) 
		set_multiple(cdt,cdn,{company:sys_defaults.company});
	if(!doc.fiscal_year && sys_defaults.fiscal_year) 
		set_multiple(cdt,cdn,{fiscal_year:sys_defaults.fiscal_year});		
	
	if(doc.enquiry_from) {
		if(doc.enquiry_from == 'Customer') {
			hide_field('lead');
		}
		else if (doc.enquiry_from == 'Lead') {
			hide_field(['customer', 'customer_address', 'contact_person', 'customer_group']);
		}
	} 

	if(!doc.__islocal) {
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: wn.model.get("Communication", {"opportunity": doc.name}),
			parent: cur_frm.fields_dict.communication_html.wrapper,
			doc: doc,
			recipients: doc.contact_email
		});
	}
	
	if(cur_frm.fields_dict.contact_by.df.options.match(/^Profile/)) {
		cur_frm.fields_dict.contact_by.get_query = erpnext.utils.profile_query;
	}
	
	if(doc.customer && !doc.customer_name) cur_frm.cscript.customer(doc);
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.enquiry_from == 'Lead' && doc.lead) {
	 	cur_frm.cscript.lead(doc,cdt,cdn);
	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		get_server_fields('get_item_details',d.item_code, 'enquiry_details',doc, cdt,cdn,1);
	}
}

// hide - unhide fields on basis of enquiry_from lead or customer
cur_frm.cscript.enquiry_from = function(doc,cdt,cdn){
	cur_frm.cscript.lead_cust_show(doc,cdt,cdn);
}

// hide - unhide fields based on lead or customer
cur_frm.cscript.lead_cust_show = function(doc,cdt,cdn){	
	if(doc.enquiry_from == 'Lead'){
		unhide_field(['lead']);
		hide_field(['customer','customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
		doc.lead = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
	}
	else if(doc.enquiry_from == 'Customer'){		
		unhide_field(['customer']);
		hide_field(['lead', 'address_display', 'contact_display', 'contact_mobile', 
			'contact_email', 'territory', 'customer_group']);		
		doc.lead = doc.customer = doc.customer_address = doc.contact_person = doc.address_display = doc.contact_display = doc.contact_mobile = doc.contact_email = doc.territory = doc.customer_group = "";
	}
}

// customer
cur_frm.cscript.customer = function(doc,dt,dn) {
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	
	if(doc.customer) {
		cur_frm.call({
			doc: cur_frm.doc,
			method: "get_default_customer_address",
			args: { customer: doc.customer },
			callback: function(r) {
				if(!r.exc) {
					cur_frm.refresh();
				}
			}
		});
		
		unhide_field(["customer_name", "customer_address", "contact_person",
			"address_display", "contact_display", "contact_mobile", "contact_email",
			"territory", "customer_group"]);
	}
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name, address_line1, city FROM tabAddress \
		WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND \
		%(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	if (!doc.customer) msgprint("Please select customer first");
	else {
		return 'SELECT name, CONCAT(first_name," ",ifnull(last_name,"")) As FullName, \
		department, designation FROM tabContact WHERE customer = "'+ doc.customer + 
		'" AND docstatus != 2 AND %(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
	}
}

// lead
cur_frm.fields_dict['lead'].get_query = function(doc,cdt,cdn){
	return 'SELECT `tabLead`.name, `tabLead`.lead_name FROM `tabLead` WHERE `tabLead`.%(key)s LIKE "%s"	ORDER BY	`tabLead`.`name` ASC LIMIT 50';
}

cur_frm.cscript.lead = function(doc, cdt, cdn) {
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	
	if(doc.lead) {
		get_server_fields('get_lead_details', doc.lead,'', doc, cdt, cdn, 1);
		unhide_field(['customer_name', 'address_display','contact_mobile', 'contact_email', 
			'territory']);	
	}
}


//item getquery
//=======================================
cur_frm.fields_dict['enquiry_details'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
	if (doc.enquiry_type == 'Maintenance')
	 	return erpnext.queries.item({
			'ifnull(tabItem.is_service_item, "No")': 'Yes'
		});
	else 
 		return erpnext.queries.item({
			'ifnull(tabItem.is_sales_item, "No")': 'Yes'
		});
}

// Create New Quotation
cur_frm.cscript['Create Quotation'] = function(){
	n = wn.model.make_new_doc_and_get_name("Quotation");
	$c('dt_map', args={
		'docs':wn.model.compress([locals["Quotation"][n]]),
		'from_doctype':'Opportunity',
		'to_doctype':'Quotation',
		'from_docname':cur_frm.docname,
		'from_to_list':"[['Opportunity', 'Quotation'],['Opportunity Item','Quotation Item']]"
	}
	, function(r,rt) {
		loaddoc("Quotation", n);
		}
	);
}


// declare enquiry	lost
//-------------------------
cur_frm.cscript['Declare Opportunity Lost'] = function(){
	var e_lost_dialog;

	set_e_lost_dialog = function(){
		e_lost_dialog = new Dialog(400,150,'Add Opportunity Lost Reason');
		e_lost_dialog.make_body([
			['HTML', 'Message', '<div class="comment">Please add enquiry lost reason</div>'],
			['Text', 'Opportunity Lost Reason'],
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
			e_lost_dialog.widgets['Opportunity Lost Reason'].value = '';
			$i('update_enquiry_dialog_response').innerHTML = '';
		}
		
		e_lost_dialog.add = function() {
			// sending...
			$i('update_enquiry_dialog_response').innerHTML = 'Processing...';
			var arg =	strip(e_lost_dialog.widgets['Opportunity Lost Reason'].value);
			var call_back = function(r,rt) { 
				if(r.message == 'true'){
					$i('update_enquiry_dialog_response').innerHTML = 'Done';
					e_lost_dialog.hide();
					cur_frm.refresh();
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
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';}
	
cur_frm.fields_dict.lead.get_query = erpnext.utils.lead_query;

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;