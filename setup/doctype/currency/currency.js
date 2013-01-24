cur_frm.cscript.refresh = function(doc) {
	cur_frm.set_intro("");
	if(!cur_frm.doc.enabled) {
		cur_frm.set_intro(wn._("This Currency is disabled. Enable to use in transactions"))
	}
}