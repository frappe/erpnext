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
wn.pages['{{ name }}'].onload = function(wrapper) {
	erpnext.blog_list = new wn.ui.Listing({
		parent: $(wrapper).find('#blog-list').get(0),
		method: 'website.blog.get_blog_list',
		hide_refresh: true,
		no_toolbar: true,
		render_row: function(parent, data) {
			if(data.content && data.content.length==1000) {
				data.content += repl('... <a href="%(name)s.html">(read on)</a>', data);
			}
			parent.innerHTML = repl('<h2><a href="%(name)s.html">%(title)s</a></h2>\
				%(content)s<br /><br />', data);
		},
		page_length: 10
	});
	erpnext.blog_list.run();
}