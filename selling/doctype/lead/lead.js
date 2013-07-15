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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

// Module CRM

wn.require('app/utilities/doctype/sms_control/sms_control.js');

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(user =='Guest'){
		hide_field(['status', 'naming_series', 'order_lost_reason',
	'customer', 'rating', 'fax', 'website', 'territory',
	'address_line1', 'address_line2', 'city', 'state',
	'country', 'pincode', 'address', 'lead_owner', 'market_segment',
	'industry', 'campaign_name', 'interested_in', 'company',
	'fiscal_year', 'contact_by', 'contact_date', 'last_contact_date',
	'contact_date_ref', 'to_discuss', 'more_info', 'follow_up',
	'communication_history', 'cc_to', 'subject', 'message', 'lead_attachment_detail',
	'Create Customer', 'Create Opportunity', 'transaction_date', 'type', 'source']);
		doc.source = 'Website';
	}
	if(!doc.status) set_multiple(dt,dn,{status:'Open'});

	if (!doc.date){ 
		doc.date = date.obj_to_str(new Date());
	}
	// set naming series
	if(user=='Guest') doc.naming_series = 'WebLead';
	
	cur_frm.add_fetch('customer', 'customer_name', 'company_name');
	
	if(cur_frm.fields_dict.lead_owner.df.options.match(/^Profile/)) {
		cur_frm.fields_dict.lead_owner.get_query = erpnext.utils.profile_query;
	}

	if(cur_frm.fields_dict.contact_by.df.options.match(/^Profile/)) {
		cur_frm.fields_dict.contact_by.get_query = erpnext.utils.profile_query;
	}

	if(in_list(user_roles,'System Manager')) {
		cur_frm.page_layout.footer.help_area.innerHTML = '<hr>\
			<p><a href="#Form/Sales Email Settings">Sales Email Settings</a><br>\
			<span class="help">Automatically extract Leads from a mail box e.g. "sales@example.com"</span></p>';
	}
}

cur_frm.cscript.refresh_custom_buttons = function(doc) {
	cur_frm.clear_custom_buttons();
	if(!doc.__islocal && !in_list(['Converted', 'Lead Lost'], doc.status)) {
		if (doc.source != 'Existing Customer') {
			cur_frm.add_custom_button('Create Customer',
				cur_frm.cscript['Create Customer']);
		}
		cur_frm.add_custom_button('Create Opportunity',
			cur_frm.cscript['Create Opportunity']);
		cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);
	}
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.refresh_custom_buttons(doc);
	erpnext.hide_naming_series();

	cur_frm.communication_view = new wn.views.CommunicationList({
		list: wn.model.get("Communication", {"lead": doc.name}),
		parent: cur_frm.fields_dict.communication_html.wrapper,
		doc: doc,
		recipients: doc.email_id
	})
}



cur_frm.cscript.status = function(doc, cdt, cdn){
	cur_frm.cscript.refresh(doc, cdt, cdn);
}

cur_frm.cscript['Create Customer'] = function(){
	var doc = cur_frm.doc;
	$c('runserverobj',args={ 'method':'check_status', 'docs':wn.model.compress(make_doclist(doc.doctype, doc.name))},
		function(r,rt){
			if(r.message == 'Converted'){
				msgprint("This lead is already converted to customer");
			}
			else{
				n = wn.model.make_new_doc_and_get_name("Customer");
				$c('dt_map', args={
					'docs':wn.model.compress([locals["Customer"][n]]),
					'from_doctype':'Lead',
					'to_doctype':'Customer',
					'from_docname':doc.name,
					'from_to_list':"[['Lead', 'Customer']]"
				}, 
				function(r,rt) {
					wn.model.with_doctype("Customer", function() {
						var customer = wn.model.get_doc("Customer", n);
						var customer_copy = $.extend({}, customer);

						var updated = wn.model.set_default_values(customer_copy);
						$.each(updated, function(i, f) {
							if(!customer[f]) customer[f] = customer_copy[f];
						});
					
						loaddoc("Customer", n);
					});
				}
				);
			}
		}
	);
}

// Create New Opportunity
// ===============================================================
cur_frm.cscript['Create Opportunity'] = function(){
	var doc = cur_frm.doc;
	$c('runserverobj',args={ 'method':'check_status', 'docs':wn.model.compress(make_doclist(doc.doctype, doc.name))},
		function(r,rt){
			if(r.message == 'Converted'){
				msgprint("This lead is now converted to customer. Please create enquiry on behalf of customer");
			}
			else{
				n = wn.model.make_new_doc_and_get_name("Opportunity");
				$c('dt_map', args={
					'docs':wn.model.compress([locals["Opportunity"][n]]),
					'from_doctype':'Lead',
					'to_doctype':'Opportunity',
					'from_docname':doc.name,
					'from_to_list':"[['Lead', 'Opportunity']]"
				}
				, function(r,rt) {
						loaddoc("Opportunity", n);
					}
				);
			}
		}
	);
}

//get query select Territory
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s" ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;