// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

// js inside blog page

$(document).ready(function() {
	var n_comments = $(".comment-row").length;
	
	if(n_comments) {
		$(".no_comment").toggle(false);
	}
	if(n_comments > 50) {
		$(".add-comment").toggle(false)
			.parent().append("<div class='alert alert-warning'>Comments are closed.</div>")
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
			comment_doctype: "Blog Post",
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
						.replaceWith("<div class='alert alert-success'>Thank you for your comment!</div>")
				}
			}
		})
		
		return false;
	})
})