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

$.extend(cur_frm.cscript, {
	onload: function(doc, dt, dn) {
		cur_frm.last_reload = new Date();
		if(in_list(user_roles,'System Manager')) {
			cur_frm.page_layout.footer.help_area.innerHTML = '<hr>\
				<p><a href="#Form/Email Settings/Email Settings">Email Settings</a><br>\
				<span class="help">Integrate incoming support emails to Support Ticket</span></p>';
		}
		
		if(!doc.customer) hide_field(['customer_name','address_display','contact_display','contact_mobile','contact_email']);		
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
		$(wrapper)
			.html("")
			.css({"margin":"10px 0px"});
		
		var comm_list = wn.model.get("Communication", {"support_ticket": doc.name})
		comm_list.push({
			"email_address": doc.raised_by,
			"modified": doc.creation,
			"content": doc.description});
			
		comm_list.sort(function(a, b) { return new Date(a.modified) > new Date(b.modified) 
			? -1 : 1 })
		
		new erpnext.CommunicationView({
			list: comm_list,
			parent: wrapper
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
		if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', '', callback);
		if(doc.customer) unhide_field(['customer_name','address_display','contact_display','contact_mobile','contact_email']);
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

erpnext.CommunicationView = Class.extend({
	init: function(opts) {
		this.comm_list = [];
		$.extend(this, opts);
		this.make();
	},
	make: function() {
		var me = this;
		this.make_body();
		$.each(this.list, function(i, d) {
			me.prepare(d);
			me.make_line(d);
		});
		// show first
		this.comm_list[0].find('.comm-content').toggle(true);
	},
	make_body: function() {
		this.wrapper = $("<div><h4>Communication History</h4></div>").appendTo(this.parent);
		this.body = $("<table class='table table-bordered table-hover table-striped'>")
			.appendTo(this.body);
	},
	prepare: function(doc) {
		//doc.when = comment_when(this.doc.modified);
		doc.when = doc.modified;
		if(doc.content.indexOf("<br>")== -1 && doc.content.indexOf("<p>")== -1) {
			doc.content = doc.content.replace(/\n/g, "<br>");
		}
		doc.email_address = doc.email_address.replace(/</, "&lt;").replace(/>/, "&gt;");
		doc.content = doc.content.split("=== In response to ===")[0];
		doc.content = doc.content.split("-----Original Message-----")[0];
	},
	make_line: function(doc) {
		var me = this;
		var comm = $(repl('<tr><td title="Click to Expand / Collapse">\
				<p><b>%(email_address)s on %(when)s</b></p>\
				<div class="comm-content"></div>\
			</td></tr>', doc))
			.appendTo(this.body)
			.css({"cursor":"pointer"})
			.click(function() {
				$(this).find(".comm-content").toggle();
			});
		
		this.comm_list.push(comm);
		comm.find(".comm-content").html(doc.content);
	}
})


cur_frm.fields_dict.allocated_to.get_query = erpnext.utils.profile_query;
cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;