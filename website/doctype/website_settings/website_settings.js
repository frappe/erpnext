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

// update parent select

$.extend(cur_frm.cscript, {
	
	onload_post_render: function(doc) {
		// get labels of parent items
		var get_parent_options = function(table_field) {
			var items = getchildren('Top Bar Item', doc.name, table_field);
			var main_items = [''];
			for(var i in items) {
				var d = items[i];
				if(!d.parent_label) {
					main_items.push(d.label);
				}
			}
			return main_items.join('\n');
		}
		
		// bind function to refresh fields
		// when "Parent Label" is select, it 
		// should automatically update
		// options
		$(cur_frm.fields_dict['top_bar_items'].grid.get_field('parent_label').wrapper)
			.bind('refresh', function() {
				this.fieldobj.refresh_options(get_parent_options('top_bar_items'));
			});
	}
});

cur_frm.cscript.set_banner_from_image = function(doc) {
	if(!doc.banner_image) {
		msgprint(wn._("Select a Banner Image first."));
	}
	var src = doc.banner_image;
	if(src.indexOf("/")==-1) src = "files/" + src;
	cur_frm.set_value("banner_html", "<a href='/'><img src='"+ src
		+"' style='max-width: 200px;'></a>");
}