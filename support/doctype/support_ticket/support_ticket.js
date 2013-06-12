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

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;

$.extend(cur_frm.cscript, {
	onload: function(doc, dt, dn) {
		if(in_list(user_roles,'System Manager')) {
			cur_frm.footer.help_area.innerHTML = '<p><a href="#Form/Email Settings/Email Settings">Email Settings</a><br>\
				<span class="help">Integrate incoming support emails to Support Ticket</span></p>';
		}
		
		if(doc.description)
			doc.description = wn.utils.escape_script_and_style(doc.description);
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
		
		var comm_list = wn.model.get("Communication", {"support_ticket": doc.name})

		var sortfn = function (a, b) { return (b.creation > a.creation) ? 1 : -1; }
		comm_list = comm_list.sort(sortfn);
		
		if(!comm_list.length || (comm_list[comm_list.length - 1].sender != doc.raised_by)) {
			comm_list.push({
				"sender": doc.raised_by,
				"creation": doc.creation,
				"modified": doc.creation,
				"content": doc.description});
		}
					
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: comm_list,
			parent: wrapper,
			doc: doc,
			recipients: doc.raised_by
		})

	},
		
	customer: function(doc, dt, dn) {
		var callback = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			if(!r.exc) {
				cur_frm.refresh();
			}
		}
		if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 
			'get_default_customer_address', '', callback);
	}, 
	
	'Close Ticket': function() {
		cur_frm.cscript.set_status("Closed");
	},
	
	'Re-Open Ticket': function() {
		cur_frm.cscript.set_status("Open");
	},

	set_status: function(status) {
		wn.call({
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

