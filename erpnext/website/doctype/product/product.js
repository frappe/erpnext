$.extend(cur_frm.cscript, {
	onload: function() {
		cur_frm.add_fetch('item', 'description', 'short_description');
		cur_frm.add_fetch('item', 'item_name', 'title');
	}
});