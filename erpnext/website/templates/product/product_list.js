{% extends "page.html" %}

{% block javascript %}
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
	erpnext.product_list = new wn.ui.Listing({
		parent: $(wrapper).find('#product-list').get(0),
		query: "select name, item_code, item_name, description, page_name \
				from `tabItem` \
				where docstatus = 0 and ifnull(show_in_website, 'No')='Yes'\
				order by item_name asc",
		hide_refresh: true,
		no_toolbar: true,
		render_row: function(parent, data) {
			if(data.description && data.description.length==1000) data.description += '... (read on)';
			parent.innerHTML = repl('<h4><a href="%(page_name)s.html">%(item_name)s</a></h4>\
				<p>%(description)s</p>', data);
		},
		page_length: 10
	});
	erpnext.product_list.run();
}

{% endblock %}
