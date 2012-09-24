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

wn.provide('erpnext.blog');
wn.pages['{{ name }}'].onload = function(wrapper) {
	erpnext.blog.wrapper = wrapper;
	
	// sidebar
	erpnext.blog.render_recent_list(wrapper);
	
	// unhide no-result if no comments found
	erpnext.blog.toggle_no_result(wrapper);
	
	// bind add comment button to comment dialog
	erpnext.blog.make_comment_dialog(wrapper);
	
	// hide add comment button after 50 comments
	erpnext.blog.toggle_add_comment_btn(wrapper);
}

erpnext.blog.adjust_page_height = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.blog.wrapper; }
	if (!wrapper) { return; }

	// adjust page height based on sidebar height
	var $main_page = $(wrapper).find('.layout-main-section');
	var $sidebar = $(wrapper).find('.layout-side-section');
	if ($sidebar.height() > $main_page.height()) {
		$main_page.height($sidebar.height());
	}
}

erpnext.blog.render_recent_list = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.blog.wrapper; }
	if (!wrapper) { return; }
	
	wrapper.recent_list = new wn.ui.Listing({
		parent: $(wrapper).find('.recent-posts'),
		no_toolbar: true,
		method: 'website.blog.get_recent_blog_list',
		get_args: function() {
			return { name: '{{ name }}' }
		},
		hide_refresh: true,
		render_row: function(parent, data) {
			if(data.content && data.content.length>=100) data.content += '...';
			parent.innerHTML = repl('<div style="font-size: 80%">\
				<a href="%(page_name)s.html">%(title)s</a>\
				<div class="comment">%(content)s</div><br></div>', data);
			
			// adjust page height depending on sidebar height
			erpnext.blog.adjust_page_height(wrapper);
		},
		page_length: 5,
	});
	wrapper.recent_list.run();
}

erpnext.blog.toggle_no_result = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.blog.wrapper; }
	if (!wrapper) { return; }
	
	var $blog_comments = $(wrapper).find('.blog-comments');
	var $comment_rows = $blog_comments.find('.comment-row');
	var $no_result = $blog_comments.find('.no-result');

	if ($comment_rows.length == 0) {
		$no_result.removeClass('hide');
	} else {
		$no_result.addClass('hide');
	}
}

erpnext.blog.make_comment_dialog = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.blog.wrapper; }
	if (!wrapper) { return; }
	
	var $comment_btn = $(wrapper).find('button.add-comment');
	
	$comment_btn.click(function() {
		if(!erpnext.blog.comment_dialog) {
			var d = new wn.widgets.Dialog({
				title: 'Add Comment',
				fields: [
					{
						fieldname: 'comment_by_fullname', label: 'Your Name',
						reqd: 1, fieldtype: 'Data'
					},
					{
						fieldname: 'comment_by', label: 'Email Id',
						reqd: 1, fieldtype: 'Data'
					},
					{
						fieldname: 'comment', label: 'Comment',
						reqd: 1, fieldtype: 'Text'
					},
					{
						fieldname: 'post_comment', label: 'Post Comment',
						fieldtype: 'Button'
					},
				],
			});
			
			erpnext.blog.comment_dialog = d;
		}
		
		erpnext.blog.comment_dialog.fields_dict.post_comment
				.input.onclick = function() {
			erpnext.blog.add_comment(wrapper);
		}
		
		erpnext.blog.comment_dialog.show();
	});

}

erpnext.blog.add_comment = function(wrapper) {
	var args = erpnext.blog.comment_dialog.get_values();

	if(!args) return;
	
	args.comment_doctype = 'Blog';
	args.comment_docname = '{{ name }}';
	args.page_name = '{{ page_name }}';
	
	wn.call({
		method: 'website.blog.add_comment',
		args: args,
		btn: this,
		callback: function(r) {
			if(!r.exc) {
				erpnext.blog.add_comment_to_page(wrapper, r.message);
				erpnext.blog.comment_dialog.hide();
			}
		}
	});
}

erpnext.blog.add_comment_to_page = function(wrapper, comment) {
	$blog_comments = $(wrapper).find('.blog-comments');
	$comment_rows = $blog_comments.find('.comment-row');
	
	if ($comment_rows.length) {
		$blog_comments.append(comment);
	} else {
		$blog_comments.append(comment);
	}
	
	erpnext.blog.toggle_no_result(wrapper);
	erpnext.blog.toggle_add_comment_btn(wrapper);
}

erpnext.blog.toggle_add_comment_btn = function(wrapper) {
	var $wrapper = $(wrapper);
	if ($wrapper.find('.blog-comments .comment-row').length > 50) {
		var $comment_btn = $wrapper.find('button.add-comment');
		$comment_btn.addClass('hide');
		
		// show comments are close
		$wrapper.find('.blog-comments').append("\
			<div class=\"help\"> \
				<p>Comments Closed</p> \
				<br /> \
			</div>");
	}
}