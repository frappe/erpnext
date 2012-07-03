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

// threading structure
// -------- orginal message --------
// xoxoxoxo
// -------- reply 1 --------
// -------- reply 2 --------
// xoxoxoxo
// -------- new reply --------

var cs = cur_frm.cscript;
$.extend(cur_frm.cscript, {
	onload: function(doc, dt, dn) {
		//
		// help area
		//
		if(in_list(user_roles,'System Manager')) {
			cur_frm.page_layout.footer.help_area.innerHTML = '';
			new wn.widgets.Footer({
				parent:cur_frm.page_layout.footer.help_area,
				columns:2,
				items: [
					{
						column: 0,
						label:'Email Settings',
						description:'Integrate your incoming support emails to support ticket',
						onclick: function() { loaddoc('Email Settings','Email Settings'); }
					}, 					
				]
			})			
		}
		
		if(!doc.customer) hide_field(['customer_name','address_display','contact_display','contact_mobile','contact_email']);		
	},
	
	refresh: function(doc) {
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
	
	//
	// make thread listing
	//
	make_listing: function(doc) {
		cur_frm.fields_dict['thread_html'].wrapper.innerHTML = '';
		
		// render first message
		new EmailMessage($a(cur_frm.fields_dict['thread_html'].wrapper, 'div'), {
			from_email: doc.raised_by,
			creation: doc.creation,
			mail: doc.description,
			content_type: doc.content_type
		}, null, -1)
		
		// render thread		
		cur_frm.cscript.thread_list = new wn.ui.Listing({
			parent: $a(cur_frm.fields_dict['thread_html'].wrapper, 'div'),
			no_result_message: 'No responses yet',
			get_query: function() {
				return 'select mail, from_email, creation, content_type '+
				'from `tabSupport Ticket Response` where parent="'+doc.name+'" order by creation asc'
			},
			as_dict: 1,
			render_row: function(parent, data, list, idx) {
				new EmailMessage(parent, data, list, idx);
			}
		});
		cur_frm.cscript.thread_list.run();

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
		
		var answer = confirm("Close Ticket "+doc.name+"?\n\nAllocated To: "+doc.allocated_to+"\n\nSubject: "+doc.subject+"");
		if(answer) {
			if(doc.name) 
				$c_obj(make_doclist(doc.doctype, doc.name),'close_ticket','',function(r,rt) {
					if(!r.exc) {
						cur_frm.refresh();
					}
				});
		}
	},
	
	'Re-Open Ticket': function() {
		var doc = cur_frm.doc
		
		var answer = confirm("Re-Open Ticket "+doc.name+"?\n\nAllocated To: "+doc.allocated_to+"\n\nSubject: "+doc.subject+"");
		if(answer) {
			if(doc.name) 
				$c_obj(make_doclist(doc.doctype, doc.name),'reopen_ticket','',function(r,rt) {
					if(!r.exc) {
						cur_frm.refresh();
					}
				});
		}
	}

	
})



EmailMessage = function(parent, args, list, idx) {
	var me = this;
	$.extend(this, args);
	this.make = function() {
		this.creation = wn.datetime.str_to_user(this.creation);
		if(this.from_email)
			this.from_email = this.from_email.replace('<', '&lt;').replace('>', '&gt;');
		
		// main wrapper
		w = $a(parent, 'div', 'support-ticket-wrapper well');
		//$(w).addClass('support-ticket-wrapper');

		// sender and timestamp
		$a($a(w, 'div', 'support-ticket-title'), 
			'span', 'link_type', {}, repl('By %(from_email)s on %(creation)s:', this), 
			function() {
				// toggle message display on timestamp
				if(me.message.style.display.toLowerCase()=='none') {
					$ds(me.message);
				} else {
					$dh(me.message);
				}
			}
		);
		
		// email text
		this.message = $a(w, 'div', '', 
			// style
			{lineHeight:'1.7em', display:'none', padding: '7px', width: '575px',
				wordWrap: 'break-word', textWrap: 'normal', overflowX: 'auto'}, 
			
			// newlines for text email
			(this.content_type=='text/plain' ? this.mail
				.replace(/\n[ ]*\n[\n\t ]*/g, '\n\n') // excess whitespace
				.replace(/\n/g, '<br>') : this.mail)
		);
		
		// show only first and last message
		if(idx==-1 || list && list.data.length-1==idx) {
			$ds(this.message)
		}
		
	}
	this.make();
}
