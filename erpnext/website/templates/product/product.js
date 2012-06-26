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

wn.require('js/product_category.js');

wn.pages['{{ name }}'].onload = function(wrapper) {
	console.log('loaded page');
	wrapper.product_group = "{{ item_group }}";
	wrapper.product_name = "{{ name }}";
	erpnext.make_product_categories(wrapper);
	$(wrapper).find('.product-inquiry').click(function() {
		loadpage('contact', function() {
			$('#content-contact-us [name="contact-message"]').val("Hello,\n\n\
			Please send me more information on {{ item_name }} (Item Code:{{ name }})\n\n\
			My contact details are:\n\nThank you!\
			");
		})
	});
	
	// similar products
	wrapper.similar = new wn.ui.Listing({
		parent: $(wrapper).find('.similar-products').get(0),
		hide_refresh: true,
		page_length: 5,
		get_query: function() {
			args = {
				cat: wrapper.product_group,
				name: wrapper.product_name
			};
			return repl('select name, item_name, website_image, \
				page_name, description \
				from tabItem \
				and ifnull(show_in_website, "No")="Yes" \
				and name != "%(name)s" \
				and item_group="%(cat)s" order by modified desc', args)
		},
		render_row: function(parent, data) {
			if(data.short_description.length > 100) {
				data.short_description = data.short_description.substr(0,100) + '...';
			}
			parent.innerHTML = repl('<div style="float:left; width: 60px;">\
				<img src="files/%(website_image)s" style="width:55px;"></div>\
				<div style="float:left; width: 180px">\
					<b><a href="%(page_name)s.html">%(item_name)s</a></b>\
					<p>%(description)s</p></div>\
				<div style="clear: both; margin-bottom: 15px;"></div>', data);
		}
	});
	wrapper.similar.run();
}

{% endblock %}