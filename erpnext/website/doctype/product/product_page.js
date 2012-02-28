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

wn.require('erpnext/website/js/product_category.js');

pscript["onload_{{ doc.page_name }}"] = function(wrapper) {
	wrapper.product_group = "{{ doc.item_group }}";
	wrapper.product_name = "{{ doc.name }}";
	erpnext.make_product_categories(wrapper);
	$(wrapper).find('.product-inquiry').click(function() {
		loadpage('contact', function() {
			$('#content-contact-us [name="contact-message"]').val("Hello,\n\n\
			Please send me more information on {{ doc.title }} (Item Code:{{ doc.item }})\n\n\
			My contact details are:\n\nThank you!\
			");
		})
	});
	
	// similar products
	wrapper.similar = new wn.widgets.Listing({
		parent: $(wrapper).find('.similar-products').get(0),
		hide_refresh: true,
		page_length: 5,
		get_query: function() {
			args = {
				cat: wrapper.product_group,
				name: wrapper.product_name
			};
			return repl('select t1.name, t1.title, t1.thumbnail_image, \
				t1.page_name, t1.short_description \
				from tabProduct t1, tabItem t2 \
				where t1.item = t2.name \
				and ifnull(t1.published,0)=1 \
				and t1.name != "%(name)s" \
				and t2.item_group="%(cat)s" order by t1.modified desc', args)
		},
		render_row: function(parent, data) {
			if(data.short_description.length > 100) {
				data.short_description = data.short_description.substr(0,100) + '...';
			}
			parent.innerHTML = repl('<div style="float:left; width: 60px;">\
				<img src="files/%(thumbnail_image)s" style="width:55px;"></div>\
				<div style="float:left; width: 180px">\
					<b><a href="#!%(page_name)s">%(title)s</a></b>\
					<p>%(short_description)s</p></div>\
				<div style="clear: both; margin-bottom: 15px;"></div>', data);
		}
	});
	wrapper.similar.run();
}