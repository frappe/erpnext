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
		this.set_parent_label_options();
	},
	
	label: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(item.parentfield === "top_bar_items") {
			this.set_parent_label_options();
		}
	},
	
	parent_label: function(doc, cdt, cdn) {
		this.label(doc, cdt, cdn);
	},
	
	url: function(doc, cdt, cdn) {
		this.label(doc, cdt, cdn);
	},
	
	set_parent_label_options: function() {
		wn.meta.get_docfield("Top Bar Item", "parent_label", cur_frm.docname).options = 
			this.get_parent_options("top_bar_items");
		
		if($(cur_frm.fields_dict.top_bar_items.grid.wrapper).find(".grid-row-open")) {
			cur_frm.fields_dict.top_bar_items.grid.refresh();
		}
	},
	
	// get labels of parent items
	get_parent_options: function(table_field) {
		var items = getchildren('Top Bar Item', cur_frm.doc.name, table_field);
		var main_items = [''];
		for(var i in items) {
			var d = items[i];
			if(!d.parent_label && !d.url && d.label) {
				main_items.push(d.label);
			}
		}
		return main_items.join('\n');
	}
});

cur_frm.cscript.set_banner_from_image = function(doc) {
	if(!doc.banner_image) {
		msgprint(wn._("Select a Banner Image first."));
	}
	var src = doc.banner_image;
	cur_frm.set_value("banner_html", "<a href='/'><img src='"+ src
		+"' style='max-width: 200px;'></a>");
}