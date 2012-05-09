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

pscript['onload_{{ doc.name }}'] = function(wrapper) {
	// sidebar
	wrapper.recent_list = new wn.ui.Listing({
		parent: $(wrapper).find('.recent-posts'),
		no_toolbar: true,
		query: 'select name, title, left(content, 100) as content from tabBlog\
			where ifnull(published,0)=1 and name!="{{ doc.name }}" order by modified desc',
		hide_refresh: true,
		render_row: function(parent, data) {
			console.log(data);
			if(data.content && data.content.length==100) data.content += '...';
			parent.innerHTML = repl('<a href="%(name)s.html">%(title)s</a>\
				<div class="comment">%(content)s</div><br>', data);
		},
		page_length: 5,
	});
	wrapper.recent_list.run();
		
	wrapper.comment_list = new wn.ui.Listing({
		parent: $(wrapper).find('.blog-comments').get(0),
		no_toolbar: true,
		query: 'select comment, comment_by_fullname, modified\
			from `tabComment` where comment_doctype="Page"\
			and comment_docname="{{ doc.name }}" order by modified desc',
		no_result_message: 'Be the first one to comment',
		render_row: function(parent, data) {
			data.comment_date = prettyDate(data.modified);
			$(parent).html(repl("<div style='color:#777'>\
				%(comment_by_fullname)s | %(comment_date)s:\
				</div>\
				<p style='margin-left: 20px;'>%(comment)s</p><br>", data))
		},
		hide_refresh: true
	});
	wrapper.comment_list.run();
	
	// add comment
	$(wrapper).find('.layout-main-section').append('<br><button class="btn add-comment">\
		Add Comment</button>');
	$(wrapper).find('button.add-comment').click(function(){
		d = new wn.widgets.Dialog({
			title: 'Add Comment',
			fields: [
				{fieldname:'comment_by_fullname', label:'Your Name', reqd:1, fieldtype:'Data'},
				{fieldname:'comment_by', label:'Email Id', reqd:1, fieldtype:'Data'},
				{fieldname:'comment', label:'Comment', reqd:1, fieldtype:'Text'},
				{fieldname:'post', label:'Post', fieldtype:'Button'}
			]
		});
		d.fields_dict.post.input.onclick = function() {
			var btn = this;
			var args = d.get_values();
			if(!args) return;
			args.comment_doctype = 'Page';
			args.comment_docname = '{{ doc.name }}';
			$(btn).set_working();
			$c('webnotes.widgets.form.comments.add_comment', args, function(r) {
				$(btn).done_working();
				d.hide();
				wrapper.comment_list.refresh();
			})
		}
		d.show();
	})
}