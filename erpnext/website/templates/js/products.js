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

{% include "js/product_category.js" %}

wn.pages['{{ name }}'].onload = function(wrapper) {
	erpnext.products.wrapper = wrapper;
	
	// make product categories in the sidebar
	erpnext.products.make_product_categories(wrapper);
	
	// make lists
	erpnext.products.make_product_list(wrapper);
	
	// bind search button or enter key
	$(wrapper).find('.products-search .btn').click(function() {
		erpnext.products.product_list.run();
	});
	
	$(wrapper).find('.products-search input').keypress(function(ev) {
		if(ev.which==13) $(wrapper).find('.products-search .btn').click();
	});
}

erpnext.products.make_product_list = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.products.wrapper; }
	if (!wrapper) { return; }
	
	erpnext.products.product_list = new wn.ui.Listing({
		parent: $(wrapper).find('#products-list').get(0),
		run_btn: $(wrapper).find('.products-search .btn').get(0),
		no_toolbar: true,
		method: 'website.product.get_product_list',
		get_args: function() {
			return {
				search: $('input[name="products-search"]').val() || '',
				product_group: erpnext.products.cur_group || '',
			};
		},
		render_row: function(parent, data) {
			if (!data.web_short_description) {
				data.web_short_description = data.description;
			}
			parent.innerHTML = repl('\
				<a href="%(page_name)s.html"><div class="img-area"></div></a>\
				<div class="product-list-description">\
					<h4><a href="%(page_name)s.html">%(item_name)s</a></h4>\
					<p>%(web_short_description)s</p></div>\
				<div style="clear: both;"></div>', data);
				
			if(data.website_image) {
				$(parent).find('.img-area').append(repl(
					'<img src="files/%(website_image)s" style="width:100px;">', data))
			} else {
				$(parent).find('.img-area').append(wn.dom.placeholder(100, 
					data.item_name));
			}
		}
	});
}

wn.pages['{{ name }}'].onshow = function(wrapper) {
	// show default product category
	erpnext.products.set_group();
}

erpnext.products.set_group = function() {
	var cat = erpnext.products.get_group();

	// get erpnext.products.default_category
	var wrapper = erpnext.products.wrapper;
	
	$(wrapper).find('h1').html(cat.label);
	erpnext.products.product_list.run();
}

erpnext.products.get_group = function() {
	route = wn.get_route();
	if(route && route.length>1) {
		// from url
		var grp = route[1];
		var label = route[1];
		erpnext.products.cur_group = grp;
	} else {
		// default
		var grp = 'Products';
		var label = 'Products';
		erpnext.products.cur_group = null;
	}
	return {grp:grp, label:label};
}