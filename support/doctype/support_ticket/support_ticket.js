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
		cur_frm.last_reload = new Date();
		if(in_list(user_roles,'System Manager')) {
			cur_frm.page_layout.footer.help_area.innerHTML = '<hr>\
				<p><a href="#Form/Email Settings/Email Settings">Email Settings</a><br>\
				<span class="help">Integrate incoming support emails to Support Ticket</span></p>';
		}
	},
	
	refresh: function(doc) {
		if(new Date() - cur_frm.last_reload > 20000) {
			cur_frm.last_reload = new Date();
			cur_frm.reload_doc();
			return;
		}
		erpnext.hide_naming_series();
		cur_frm.cscript.make_listing(doc);
		if(!doc.__islocal) {											
			if(in_list(user_roles,'System Manager')) {
		      if(doc.status!='Closed') cur_frm.add_custom_button('Close Ticket', cur_frm.cscript['Close Ticket']);	
			  if(doc.status=='Closed') cur_frm.add_custom_button('Re-Open Ticket', cur_frm.cscript['Re-Open Ticket']);		
			}else if(doc.allocated_to) {
			  set_field_permlevel('status',2);
			  if(user==doc.allocated_to && doc.status!='Closed') cur_frm.add_custom_button('Close Ticket', cur_frm.cscript['Close Ticket']);
			}
			
			// can't change the main message & subject once set  
			set_field_permlevel('subject',2);
			set_field_permlevel('description',2);
			set_field_permlevel('raised_by',2);
		}
		refresh_field('status');
	},
	
	make_listing: function(doc) {
		var wrapper = cur_frm.fields_dict['thread_html'].wrapper;
		
		var comm_list = wn.model.get("Communication", {"support_ticket": doc.name})
		comm_list.push({
			"sender": doc.raised_by,
			"modified": doc.creation,
			"content": doc.description});
					
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: comm_list,
			parent: wrapper,
			doc: doc,
			email: doc.raised_by
		})

	},
	
	send: function(doc, dt, dn) {
		$c_obj(make_doclist(doc.doctype, doc.name), 'send_response', '', function(r,rt) {
			locals[dt][dn].new_response = '';
			if(!(r.exc || r.server_messages)) {
				cur_frm.refresh();
			}
		});
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
		var doc = cur_frm.doc		
		if(doc.name) 
			$c_obj(make_doclist(doc.doctype, doc.name),'close_ticket','',function(r,rt) {
				if(!r.exc) {
					cur_frm.refresh();
				}
			});
	},
	
	'Re-Open Ticket': function() {
		var doc = cur_frm.doc		
		if(doc.name) 
			$c_obj(make_doclist(doc.doctype, doc.name),'reopen_ticket','',function(r,rt) {
				if(!r.exc) {
					cur_frm.refresh();
				}
			});
	}

	
})

