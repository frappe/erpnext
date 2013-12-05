// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require('app/utilities/doctype/sms_control/sms_control.js');

wn.provide("erpnext.selling");
// TODO commonify this code
erpnext.selling.Opportunity = wn.ui.form.Controller.extend({
	onload: function() {
		if(!this.frm.doc.enquiry_from && this.frm.doc.customer)
			this.frm.doc.enquiry_from = "Customer";
		if(!this.frm.doc.enquiry_from && this.frm.doc.lead)
			this.frm.doc.enquiry_from = "Lead";

		if(!this.frm.doc.enquiry_from) 
			hide_field(['customer', 'customer_address', 'contact_person', 'customer_name','lead', 'address_display', 'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']);
		if(!this.frm.doc.status) 
			set_multiple(cdt,cdn,{status:'Draft'});
		if(!this.frm.doc.date) 
			this.frm.doc.transaction_date = date.obj_to_str(new Date());
		if(!this.frm.doc.company && wn.defaults.get_default("company")) 
			set_multiple(cdt,cdn,{company:wn.defaults.get_default("company")});
		if(!this.frm.doc.fiscal_year && sys_defaults.fiscal_year) 
			set_multiple(cdt,cdn,{fiscal_year:sys_defaults.fiscal_year});		
	
		if(this.frm.doc.enquiry_from) {
			if(this.frm.doc.enquiry_from == 'Customer') {
				hide_field('lead');
			}
			else if (this.frm.doc.enquiry_from == 'Lead') {
				hide_field(['customer', 'customer_address', 'contact_person', 'customer_group']);
			}
		} 

		if(!this.frm.doc.__islocal) {
			cur_frm.communication_view = new wn.views.CommunicationList({
				list: wn.model.get("Communication", {"opportunity": this.frm.doc.name}),
				parent: cur_frm.fields_dict.communication_html.wrapper,
				doc: this.frm.doc,
				recipients: this.frm.doc.contact_email
			});
		}
		
		if(this.frm.doc.customer && !this.frm.doc.customer_name) cur_frm.cscript.customer(this.frm.doc);
		
		this.setup_queries();
	},
	
	setup_queries: function() {
		var me = this;
		
		if(this.frm.fields_dict.contact_by.df.options.match(/^Profile/)) {
			this.frm.set_query("contact_by", erpnext.queries.profile);
		}
		
		this.frm.set_query("customer_address", function() {
			if(me.frm.doc.lead) return {filters: { lead: me.frm.doc.lead } };
			else if(me.frm.doc.customer) return {filters: { customer: me.frm.doc.customer } };
		});
		
		this.frm.set_query("item_code", "enquiry_details", function() {
			return {
				query: "controllers.queries.item_query",
				filters: me.frm.doc.enquiry_type === "Maintenance" ? 
					{"is_service_item": "Yes"} : {"is_sales_item": "Yes"}
			};
		});
		
		$.each([["lead", "lead"],
			["customer", "customer"],
			["contact_person", "customer_filter"],
			["territory", "not_a_group_filter"]], function(i, opts) {
				me.frm.set_query(opts[0], erpnext.queries[opts[1]]);
			});
	},
	
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			// TODO shift this to depends_on
			unhide_field(['customer_address', 'contact_person', 'customer_name',
				'address_display', 'contact_display', 'contact_mobile', 'contact_email', 
				'territory', 'customer_group']);
				
			return this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
			});
		}
	}, 
	
	create_quotation: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.opportunity.opportunity.make_quotation",
			source_name: cur_frm.doc.name
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.selling.Opportunity({frm: cur_frm}));

cur_frm.cscript.refresh = function(doc, cdt, cdn){
	erpnext.hide_naming_series();
	cur_frm.clear_custom_buttons();
	
	if(doc.docstatus === 1 && doc.status!=="Lost") {
		cur_frm.add_custom_button(wn._('Create Quotation'), cur_frm.cscript.create_quotation);
		if(doc.status!=="Quotation") {
			cur_frm.add_custom_button(wn._('Opportunity Lost'), cur_frm.cscript['Declare Opportunity Lost']);
		}
		cur_frm.add_custom_button(wn._('Send SMS'), cur_frm.cscript.send_sms, "icon-mobile-phone");
	}
	
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.enquiry_from == 'Lead' && doc.lead) {
	 	cur_frm.cscript.lead(doc,cdt,cdn);
	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return get_server_fields('get_item_details',d.item_code, 'enquiry_details',doc, cdt,cdn,1);
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

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc, dt, dn) {
	args = {
		address: doc.customer_address, 
		contact: doc.contact_person
	}
	if(doc.customer) args.update({customer: doc.customer});
	
	return get_server_fields('get_customer_address', JSON.stringify(args),'', doc, dt, dn, 1);
}

cur_frm.cscript.lead = function(doc, cdt, cdn) {
	cur_frm.toggle_display("contact_info", doc.customer || doc.lead);
	
	wn.model.map_current_doc({
		method: "selling.doctype.lead.lead.make_opportunity",
		source_name: cur_frm.doc.lead
	})
	
	unhide_field(['customer_name', 'address_display','contact_mobile', 'customer_address', 
		'contact_email', 'territory']);	
}



cur_frm.cscript['Declare Opportunity Lost'] = function(){
	var dialog = new wn.ui.Dialog({
		title: wn._("Set as Lost"),
		fields: [
			{"fieldtype": "Text", "label": wn._("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": wn._("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			doc: cur_frm.doc,
			method: "declare_enquiry_lost",
			args: args.reason,
			callback: function(r) {
				if(r.exc) {
					msgprint(wn._("There were errors."));
					return;
				}
				dialog.hide();
			},
			btn: this
		})
	});
	dialog.show();
	
}