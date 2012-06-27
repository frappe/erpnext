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

erpnext.make_product_categories = function(wrapper) {
	wrapper.category_list = new wn.ui.Listing({
		parent: $(wrapper).find('.more-categories').get(0),
		query: 'select count(name) as items, item_group \
			from tabItem \
			where is_sales_item="Yes" and \
			ifnull(show_in_website, "No")="Yes" and \
			docstatus = 0 \
			group by item_group order by items desc',
		hide_refresh: true,
		render_row: function(parent, data) {
			parent.innerHTML = repl('<a href="#!products/%(item_group)s">%(item_group)s</a> (%(items)s)', 
				data);
		}
	});
	wrapper.category_list.run();
	console.log('product categories made');
}
