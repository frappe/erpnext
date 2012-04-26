$.extend(cur_frm.cscript, {
	layout: function(doc) {
		if(!doc.layout) doc.layout = 'Two column with header'
		hide_field(['head_section', 'side_section', 'javascript', 'css']);
		if(doc.layout=='Two column with header') {
			unhide_field(['head_section', 'side_section']);
		}
		if(doc.layout=='Two column') {
			unhide_field('side_section');
		}
		if(doc.insert_code) {
			if(!doc.javascript) {
				doc.javascript = 'wn.pages["'+doc.name+'"].onload = function(wrapper) { }';				
			}
			unhide_field('javascript');
		}
		if(doc.insert_style) {
			if(!doc.css) {
				doc.css = '#page-'+doc.name+' { }';	
			}
			unhide_field('css');
		}
	},
	refresh: function(doc) {
		cur_frm.cscript.layout(doc);
	},
	insert_style: function(doc) {
		cur_frm.cscript.layout(doc);		
	},
	insert_code: function(doc) {
		cur_frm.cscript.layout(doc);		
	}
})