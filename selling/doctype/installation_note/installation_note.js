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
		
		this.frm.set_query("territory", function() {
			return {
				filters: {'is_group': "No" }
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
			this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
				callback: function(r) {
					if(!r.exc) me.frm.refresh_fields();
				}
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
			this.frm.call({
				doc: this.frm.doc,
				args: {
					customer: this.frm.doc.customer, 
					address: this.frm.doc.customer_address, 
					contact: this.frm.doc.contact_person
				},
				method: "get_customer_address",
				freeze: true,
				callback: function(r) {
					me.frm.refresh_fields();
				}
			});
		}
	},
	
	contact_person: function() {
		this.customer_address();
	},
});

$.extend(cur_frm.cscript, new erpnext.selling.InstallationNote({frm: cur_frm}));