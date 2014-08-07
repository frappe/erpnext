// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Installation Note Item";
cur_frm.cscript.fname = "installed_item_details";


frappe.ui.form.on_change("Installation Note", "customer",
	function(frm) { erpnext.utils.get_party_details(frm); });

frappe.ui.form.on_change("Installation Note", "customer_address",
	function(frm) { erpnext.utils.get_address_display(frm); });

frappe.ui.form.on_change("Installation Note", "contact_person",
	function(frm) { erpnext.utils.get_contact_details(frm); });

frappe.provide("erpnext.selling");
// TODO commonify this code
erpnext.selling.InstallationNote = frappe.ui.form.Controller.extend({
	onload: function() {
		if(!this.frm.doc.status) set_multiple(dt,dn,{ status:'Draft'});
		if(this.frm.doc.__islocal) set_multiple(this.frm.doc.doctype, this.frm.doc.name,
				{inst_date: get_today()});

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
				query: "erpnext.controllers.queries.customer_query"
			}
		});
	},

	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Delivery Note'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.stock.doctype.delivery_note.delivery_note.make_installation_note",
						source_doctype: "Delivery Note",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_installed: ["<", 99.99],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default"
			);
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.selling.InstallationNote({frm: cur_frm}));
