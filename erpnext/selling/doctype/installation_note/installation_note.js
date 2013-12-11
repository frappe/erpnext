// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Installation Note Item";
cur_frm.cscript.fname = "installed_item_details";

wn.provide("erpnext.selling");
// TODO commonify this code
erpnext.selling.InstallationNote = wn.ui.form.Controller.extend({
	onload: function() {
		if(!this.frm.doc.status) set_multiple(dt,dn,{ status:'Draft'});
		if(this.frm.doc.__islocal) set_multiple(this.frm.doc.doctype, this.frm.doc.name, 
				{inst_date: get_today()});
				
		fields = ['customer_address', 'contact_person','customer_name', 'address_display', 
			'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']
		if(this.frm.doc.customer) unhide_field(fields);
		else hide_field(fields)
		
		this.setup_queries();
	},
	
	setup_queries: function() {
		var me = this;
		
		this.frm.set_query("customer_address", function() {
			return {
				filters: {'customer': me.frm.doc.customer }
			}
		});
		
		this.frm.set_query("contact_person", function() {
			return {
				filters: {'customer': me.frm.doc.customer }
			}
		});
		
		this.frm.set_query("customer", function() {
			return {
				query: "controllers.queries.customer_query"
			}
		});
	},
	
	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Delivery Note'), 
				function() {
					wn.model.map_current_doc({
						method: "stock.doctype.delivery_note.delivery_note.make_installation_note",
						source_doctype: "Delivery Note",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_installed: ["<", 99.99],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}
			);
		}
	},
	
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
			});
			
			// TODO shift this to depends_on
			unhide_field(['customer_address', 'contact_person', 'customer_name',
				'address_display', 'contact_display', 'contact_mobile', 'contact_email', 
				'territory', 'customer_group']);
		}
	}, 
	
	customer_address: function() {
		var me = this;
		if(this.frm.doc.customer) {
			return this.frm.call({
				doc: this.frm.doc,
				args: {
					customer: this.frm.doc.customer, 
					address: this.frm.doc.customer_address, 
					contact: this.frm.doc.contact_person
				},
				method: "get_customer_address",
				freeze: true,
			});
		}
	},
	
	contact_person: function() {
		this.customer_address();
	},
});

$.extend(cur_frm.cscript, new erpnext.selling.InstallationNote({frm: cur_frm}));