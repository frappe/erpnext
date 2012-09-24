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

{% include "js/product_category.js" %}

wn.pages['{{ name }}'].onload = function(wrapper) {
	wrapper.product_group = "{{ item_group }}";
	wrapper.product_name = "{{ name }}";
	erpnext.products.make_product_categories(wrapper);
	erpnext.products.make_similar_products(wrapper);

	// if website image missing, autogenerate one
	var $img = $(wrapper).find('.product-page-content .img-area');
	if ($img && $img.length > 0) {
		$img.append(wn.dom.placeholder(160, "{{ item_name }}"));
	}
	
	erpnext.products.adjust_page_height(wrapper);
	
}

erpnext.products.adjust_page_height = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.products.wrapper; }
	if (!wrapper) { return; }

	// adjust page height based on sidebar height
	var $main_page = $(wrapper).find('.layout-main-section');
	var $sidebar = $(wrapper).find('.layout-side-section');
	if ($sidebar.height() > $main_page.height()) {
		$main_page.height($sidebar.height());
	}
}

erpnext.products.make_similar_products = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.products.wrapper; }
	if (!wrapper) { return; }
	
	// similar products
	wrapper.similar = new wn.ui.Listing({
		parent: $(wrapper).find('.similar-products').get(0),
		hide_refresh: true,
		page_length: 5,
		method: 'website.product.get_similar_product_list',
		get_args: function() {
			return {
				product_group: wrapper.product_group,
				product_name: wrapper.product_name
			}
		},
		render_row: function(parent, data) {
			if (!data.web_short_description) {
				data.web_short_description = data.description;
			}
			if(data.web_short_description.length > 100) {
				data.web_short_description = 
					data.web_short_description.substr(0,100) + '...';
			}
			parent.innerHTML = repl('\
				<a href="%(page_name)s.html"><div class="img-area"></div></a>\
				<div class="similar-product-description">\
					<h5><a href="%(page_name)s.html">%(item_name)s</a></h5>\
					<span>%(web_short_description)s</span>\
				</div>\
				<div style="clear:both"></div>', data);
				
			if(data.website_image) {
				$(parent).find('.img-area').append(repl(
					'<img src="files/%(website_image)s" />', data))
			} else {
				$(parent).find('.img-area').append(wn.dom.placeholder(55, 
					data.item_name));
			}
			
			// adjust page height, if sidebar height keeps increasing
			erpnext.products.adjust_page_height(wrapper);
		}
	});
	wrapper.similar.run();
}