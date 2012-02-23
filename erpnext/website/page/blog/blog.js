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


pscript.onload_blog = function(wrapper) {
	wrapper.blog_list = new wn.widgets.Listing({
		parent: $(wrapper).find('.web-main-section').get(0),
		query: 'select tabBlog.name, title, left(content, 300) as content, tabBlog.modified, \
			ifnull(first_name, "") as first_name, ifnull(last_name, "") as last_name \
			from tabProfile, tabBlog\
		 	where ifnull(published,1)=1 and tabBlog.owner = tabProfile.name',
		hide_refresh: true,
		render_row: function(parent, data) {
			if(data.content.length==300) data.content += '...';
			data.date = prettyDate(data.modified);
			parent.innerHTML = repl('<h3><a href="#!%(name)s">%(title)s</a></h3>\
				<p><div class="help">By %(first_name)s %(last_name)s on %(date)s</div></p>\
				<div class="comment">%(content)s</div><br>', data);
		},
		page_length: 10
	});
	wrapper.blog_list.run();
	
	// subscribe button
	$('#blog-subscribe').click(function() {
		var email = $(wrapper).find('input[name="blog-subscribe"]').val();
		if(!validate_email(email)) {
			msgprint('Please enter a valid email!');
		}
		wn.call({
			module:'website',
			page:'blog',
			method:'subscribe',
			args:email,
			btn: this,
			callback: function() {
				$(wrapper).find('input[name="blog-subscribe"]').val('');
			}
		});		
	})
}