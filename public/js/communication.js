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
		$.each(this.list, function(i, d) {
			me.prepare(d);
			me.make_line(d);
		});
		// show first
		this.comm_list[0].find('.comm-content').toggle(true);
	},
	make_body: function() {
		$(this.parent)
			.html("")
			.css({"margin":"10px 0px"});
			
		this.wrapper = $("<div><h4>Communication History</h4>\
			<button class='btn btn-small'>Add Reply</button></p></div>")
			.appendTo(this.parent).css({
				"overflow-x": "auto",
			});
			
		this.body = $("<table class='table table-bordered table-hover table-striped'>")
			.appendTo(this.wrapper);
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
