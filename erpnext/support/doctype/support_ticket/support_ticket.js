// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{	query:"controllers.queries.customer_query" } }

wn.provide("erpnext.support");
// TODO commonify this code
erpnext.support.SupportTicket = wn.ui.form.Controller.extend({
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
			});			
		}
	}
});

$.extend(cur_frm.cscript, new erpnext.support.SupportTicket({frm: cur_frm}));

$.extend(cur_frm.cscript, {
	onload: function(doc, dt, dn) {
		if(in_list(user_roles,'System Manager')) {
			cur_frm.footer.help_area.innerHTML = '<p><a href="#Form/Email Settings/Email Settings">'+wn._("Email Settings")+'</a><br>\
				<span class="help">'+wn._("Integrate incoming support emails to Support Ticket")+'</span></p>';
		}
	},
	
	refresh: function(doc) {
		erpnext.hide_naming_series();
		cur_frm.cscript.make_listing(doc);
		if(!doc.__islocal) {
			if(cur_frm.fields_dict.status.get_status()=="Write") {
				if(doc.status!='Closed') cur_frm.add_custom_button('Close Ticket', cur_frm.cscript['Close Ticket']);
				if(doc.status=='Closed') cur_frm.add_custom_button('Re-Open Ticket', cur_frm.cscript['Re-Open Ticket']);
			}
			
			cur_frm.toggle_enable(["subject", "raised_by"], false);
			cur_frm.toggle_display("description", false);
		}
		refresh_field('status');
	},
	
	make_listing: function(doc) {
		var wrapper = cur_frm.fields_dict['thread_html'].wrapper;
		
		var comm_list = wn.model.get("Communication", {"parent": doc.name, "parenttype":"Support Ticket"})
		
		if(!comm_list.length) {
			comm_list.push({
				"sender": doc.raised_by,
				"creation": doc.creation,
				"subject": doc.subject,
				"content": doc.description});
		}
					
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: comm_list,
			parent: wrapper,
			doc: doc,
			recipients: doc.raised_by
		})

	},
		
	'Close Ticket': function() {
		cur_frm.cscript.set_status("Closed");
	},
	
	'Re-Open Ticket': function() {
		cur_frm.cscript.set_status("Open");
	},

	set_status: function(status) {
		return wn.call({
			method:"support.doctype.support_ticket.support_ticket.set_status",
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

