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

// make sidelisting of categories
erpnext.product_item_group = {}

erpnext.make_product_categories = function(wrapper) {
	wrapper.category_list = new wn.widgets.Listing({
		parent: $(wrapper).find('.more-categories').get(0),
		query: 'select label, count(t2.name) as items, t1.item_group \
			from `tabProduct Group` t1, `tabProduct` t2, tabItem t3\
			where t1.parent="Products Settings" \
			and t2.item = t3.name \
			and t3.item_group = t1.item_group \
			and ifnull(t2.published, 0)=1 \
			group by t1.item_group \
			order by t1.idx',
		hide_refresh: true,
		render_row: function(parent, data) {
			parent.innerHTML = repl('<a href="#!products/%(label)s">%(label)s</a> (%(items)s)', 
				data);
			erpnext.product_item_group[data.label] = data.item_group;
		}
	});
	wrapper.category_list.run();	
}
