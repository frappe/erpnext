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

// js inside blog page

$(document).ready(function() {
	// make list of blogs
	blog.get_list();
	
	$("#next-page").click(function() {
		blog.get_list();
	})
});

var blog = {
	start: 0,
	get_list: function() {
		$.ajax({
			method: "GET",
			url: "server.py",
			data: {
				cmd: "website.helpers.blog.get_blog_list",
				start: blog.start
			},
			dataType: "json",
			success: function(data) {
				blog.render(data.message);
			}
		});
	},
	render: function(data) {
		var $wrap = $("#blog-list");
		$.each(data, function(i, b) {
			// comments
			if(!b.comments) {
				b.comment_text = 'No comments yet.'
			} else if (b.comments===1) {
				b.comment_text = '1 comment.'
			} else {
				b.comment_text = b.comments + ' comments.'
			} 
			
			$(repl('<h2><a href="%(page_name)s">%(title)s</a></h2>\
				<div class="help">%(comment_text)s</div>\
				%(content)s<br />\
				<p><a href="%(page_name)s">Read with comments...</a></p>\
				<hr /><br />', b)).appendTo($wrap);
		});
		blog.start += (data.length || 0);
		if(!data.length) {
			if(blog.start) {
				$("#next-page").toggle(false)
					.parent().append("<div class='alert'>Nothing more to show.</div>");	
			} else {
				$("#next-page").toggle(false)
					.parent().append("<div class='alert'>No blogs written yet.</div>");	
			}
		} else {
			$("#next-page").toggle(true);
		}
	}
}