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
	var n_comments = $(".comment-row").length;
	
	if(n_comments) {
		$(".no_comment").toggle(false);
	}
	if(n_comments > 50) {
		$(".add-comment").toggle(false)
			.parent().append("<div class='alert'>Comments are closed.</div>")
	}
	$(".add-comment").click(function() {
		$("#comment-form").toggle();
		$("#comment-form input, #comment-form, textarea").val("");
	})
	$("#submit-comment").click(function() {
		var args = {
			comment_by_fullname: $("[name='comment_by_fullname']").val(),
			comment_by: $("[name='comment_by']").val(),
			comment: $("[name='comment']").val(),
			cmd: "website.helpers.blog.add_comment",
			comment_doctype: "Blog",
			comment_docname: "{{ name }}",
			page_name: "{{ page_name }}",
			_type: "POST"
		}
		
		$("#comment-form .alert").toggle(false);
		
		if(!args.comment_by_fullname || !args.comment_by || !args.comment) {
			$("#comment-form .alert")
				.html("All fields are necessary to submit the comment.")
				.toggle(true);
			return false;
		}
		
		
		$.ajax({
			type: "POST",
			url: "server.py",
			data: args,
			dataType: "json",
			success: function(data) {
				if(data.exc) {
					$("#comment-form .alert")
						.html(data.exc)
						.toggle(true)
				} else {
					$(data.message).appendTo(".blog-comments");
					$(".no_comment").toggle(false);
					$(".add-comment").toggle(false);
					$("#comment-form")
						.replaceWith("<div class='alert'>Thank you for your comment!</div>")
				}
			}
		})
		
		return false;
	})
})