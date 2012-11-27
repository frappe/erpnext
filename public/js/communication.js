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

// opts - parent, list, doc, email
erpnext.CommunicationView = Class.extend({
	init: function(opts) {
		this.comm_list = [];
		$.extend(this, opts);
		
		this.list.sort(function(a, b) { return 
			(new Date(a.modified) > new Date(b.modified)) 
			? -1 : 1; })
				
		this.make();
	},
	make: function() {
		var me = this;
		this.make_body();

		if(this.list && this.list.length) {
			$.each(this.list, function(i, d) {
				me.prepare(d);
				me.make_line(d);
			});			
			// show first
			this.comm_list[0].find('.comm-content').toggle(true);			
		} else {
			this.body.remove()
			$("<div class='alert'>No Communication with this " 
				+ this.doc.doctype +" yet.</div>").appendTo(this.wrapper);
		}
		
	},
	make_body: function() {
		$(this.parent)
			.html("")
			.css({"margin":"10px 0px"});
			
		this.wrapper = $("<div><h4>Communication History</h4>\
			<div style='margin-bottom: 8px;'>\
				<button class='btn btn-small' \
					onclick='cur_frm.communication_view.add_reply()'>\
				<i class='icon-plus'></i> Add Reply</button></div>\
			</div>")
			.appendTo(this.parent);
			
		this.body = $("<table class='table table-bordered table-hover table-striped'>")
			.appendTo(this.wrapper);
	},
	add_reply: function() {
		var me = this;
		var d = new wn.ui.Dialog({
			width: 640,
			title: "Add Reply: " + (this.doc.subject || ""),
			fields: [
				{label:"Subject", fieldtype:"Data", reqd: 1},
				{label:"Message", fieldtype:"Text Editor", reqd: 1, fieldname:"content"},
				{label:"Send Email", fieldtype:"Check"},
				{label:"Send", fieldtype:"Button"},
			]
		});
		
		$(d.fields_dict.send_email.input).attr("checked", "checked")
		$(d.fields_dict.send.input).click(function() {
			var args = d.get_values();
			if(!args) return;
			wn.call({
				method:"support.doctype.communication.communication.make",
				args: $.extend(args, {
					doctype: me.doc.doctype,
					name: me.doc.name,
					lead: me.doc.lead,
					contact: me.doc.contact,
					recipients: me.email
				}),
				callback: function(r) {
					d.hide();
					cur_frm.reload_doc();
				}
			});
		});
		
		d.fields_dict.content.input.set_input("<p></p><p></p>=== In response to ===<p></p>" 
			+ me.list[0].content)
		$(d.fields_dict.subject.input).val(this.doc.subject || "").change();
		
		d.show();
	},

	prepare: function(doc) {
		//doc.when = comment_when(this.doc.modified);
		doc.when = doc.modified;
		if(doc.content.indexOf("<br>")== -1 && doc.content.indexOf("<p>")== -1) {
			doc.content = doc.content.replace(/\n/g, "<br>");
		}
		if(!doc.sender) doc.sender = "[unknown sender]";
		doc.sender = doc.sender.replace(/</, "&lt;").replace(/>/, "&gt;");
		doc.content = doc.content.split("=== In response to ===")[0];
		doc.content = doc.content.split("-----Original Message-----")[0];
	},
	make_line: function(doc) {
		var me = this;
		var comm = $(repl('<tr><td title="Click to Expand / Collapse">\
				<p><b>%(sender)s on %(when)s</b> \
					<a href="#Form/Communication/%(name)s" style="font-size: 90%">\
						Show Details</a></p>\
				<div class="comm-content" style="border-top: 1px solid #ddd; padding: 10px; \
					display: none;"></div>\
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
