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