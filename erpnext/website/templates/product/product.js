{% extends "product/product_category.js" %}

{% block javascript %}
{{ super() }}
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
wn.provide('erpnext.products');
wn.pages['{{ name }}'].onload = function(wrapper) {
	wrapper.product_group = "{{ item_group }}";
	wrapper.product_name = "{{ name }}";
	erpnext.products.make_product_categories(wrapper);
	
	// TODO make this working
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
			var query = repl('select name, item_name, website_image, \
				page_name, description \
				from tabItem \
				where is_sales_item="Yes" \
				and ifnull(show_in_website, "No")="Yes" \
				and name != "%(name)s" and docstatus = 0 \
				and item_group="%(cat)s" order by modified desc', args)
			return query
		},
		render_row: function(parent, data) {
			if(data.description.length > 100) {
				data.description = data.description.substr(0,100) + '...';
			}
			parent.innerHTML = repl('\
				<div style="float:left; width: 60px; padding-bottom: 5px" class="img-area"></div>\
				<div style="float:left; width: 180px">\
					<b><a href="%(page_name)s.html">%(item_name)s</a></b>\
					<p>%(description)s</p></div>\
				<div style="clear: both; margin-bottom: 15px;"></div>', data);
				
			if(data.website_image) {
				$(parent).find('.img-area').append(repl(
					'<img src="files/%(website_image)s" style="width:55px;">', data))
			} else {
				$(parent).find('.img-area').append(wn.dom.placeholder(50, 
					data.item_name));
			}
		}
	});
	wrapper.similar.run();
}

{% endblock %}