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

wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/setup/doctype/contact_control/contact_control.js');

wn.provide("erpnext");
erpnext.LeadController = wn.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.customer.get_query = erpnext.utils.customer_query;
	},
	
	onload: function() {
		if(cur_frm.fields_dict.lead_owner.df.options.match(/^Profile/)) {
			cur_frm.fields_dict.lead_owner.get_query = erpnext.utils.profile_query;
		}

		if(cur_frm.fields_dict.contact_by.df.options.match(/^Profile/)) {
			cur_frm.fields_dict.contact_by.get_query = erpnext.utils.profile_query;
		}

		if(in_list(user_roles,'System Manager')) {
			cur_frm.footer.help_area.innerHTML = '<hr>\
				<p><a href="#Form/Sales Email Settings">Sales Email Settings</a><br>\
				<span class="help">Automatically extract Leads from a mail box e.g. "sales@example.com"</span></p>';
		}
	},
	
	refresh: function() {
		var doc = this.frm.doc;
		erpnext.hide_naming_series();
		this.frm.clear_custom_buttons();
		
		this.frm.dashboard.reset(doc);
		if(!doc.__islocal) {
			if(doc.status=="Converted") {
				this.frm.dashboard.set_headline_alert(wn._("Converted"), "alert-success", "icon-ok-sign");
			} else {
				this.frm.dashboard.set_headline_alert(wn._(doc.status), "alert-info", "icon-exclamation-sign");
			}
		}
		
		this.frm.__is_customer = this.frm.__is_customer || this.frm.doc.__is_customer;
		if(!this.frm.doc.__islocal && !this.frm.__is_customer) {
			this.frm.add_custom_button("Create Customer", this.frm.cscript['Create Customer']);
			this.frm.add_custom_button("Create Opportunity", this.frm.cscript['Create Opportunity']);
			this.frm.add_custom_button("Send SMS", this.frm.cscript.send_sms);
		}
		
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: wn.model.get("Communication", {"lead": this.frm.doc.name}),
			parent: this.frm.fields_dict.communication_html.wrapper,
			doc: this.frm.doc,
			recipients: this.frm.doc.email_id
		});
		
		if(!this.frm.doc.__islocal) {
			this.make_address_list();
		}
	},
	
	make_address_list: function() {
		var me = this;
		if(!this.frm.address_list) {
			this.frm.address_list = new wn.ui.Listing({
				parent: this.frm.fields_dict['address_html'].wrapper,
				page_length: 5,
				new_doctype: "Address",
				get_query: function() {
					return 'select name, address_type, address_line1, address_line2, \
					city, state, country, pincode, fax, email_id, phone, \
					is_primary_address, is_shipping_address from tabAddress \
					where lead="'+me.frm.doc.name+'" and docstatus != 2 \
					order by is_primary_address, is_shipping_address desc'
				},
				as_dict: 1,
				no_results_message: 'No addresses created',
				render_row: this.render_address_row,
			});
			// note: render_address_row is defined in contact_control.js
		}
		this.frm.address_list.run();
	}
});

$.extend(cur_frm.cscript, new erpnext.LeadController({frm: cur_frm}));

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