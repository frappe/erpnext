// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{	query: "erpnext.controllers.queries.customer_query" } }

frappe.provide("erpnext.support");

cur_frm.add_fetch("customer", "customer_name", "customer_name")
cur_frm.email_field = "raised_by";

$.extend(cur_frm.cscript, {
	refresh: function(doc) {
		erpnext.toggle_naming_series();
		if(!doc.__islocal) {
			if(cur_frm.fields_dict.status.get_status()=="Write") {
				if(doc.status!='Closed') cur_frm.add_custom_button('Close',
					cur_frm.cscript['Close Ticket'], "icon-ok", "btn-success");
				if(doc.status=='Closed') cur_frm.add_custom_button('Re-Open Ticket',
					cur_frm.cscript['Re-Open Ticket'], null, "btn-default");
			}

			cur_frm.toggle_enable(["subject", "raised_by"], false);
			cur_frm.toggle_display("description", false);
		}
		refresh_field('status');
	},

	'Close Ticket': function() {
		cur_frm.cscript.set_status("Closed");
	},

	'Re-Open Ticket': function() {
		cur_frm.cscript.set_status("Open");
	},

	set_status: function(status) {
		return frappe.call({
			method: "erpnext.support.doctype.support_ticket.support_ticket.set_status",
			args: {
				name: cur_frm.doc.name,
				status: status
			},
			callback: function(r) {
				if(!r.exc) cur_frm.reload_doc();
			}
		})

	}

})

