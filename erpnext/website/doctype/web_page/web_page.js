$.extend(cur_frm.cscript, {
	layout: function(doc) {
		if(!doc.layout) doc.layout = 'Two column with header'
		hide_field(['head_section', 'side_section']);
		if(doc.layout=='Two column with header') {
			unhide_field(['head_section', 'side_section']);
		}
		if(doc.layout=='Two column') {
			unhide_field('side_section');
		}
	},
	refresh: function(doc) {
		cur_frm.cscript.layout(doc);
	}
})