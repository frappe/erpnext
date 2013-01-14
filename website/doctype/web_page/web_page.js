$.extend(cur_frm.cscript, {
	layout: function(doc) {
		if(!doc.__islocal) {
			if(doc.insert_code) {
				if(!doc.javascript) {
					cur_frm.set_value("javascript", 
						'wn.pages["'+doc.name+'"].onload = function(wrapper) { }');
				}
			}
			if(doc.insert_style) {
				if(!doc.css) {
					cur_frm.set_value("css", '#page-'+doc.name+' { }');	
				}
			}
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