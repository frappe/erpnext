cur_frm.cscript.refresh = function(doc) {
	cur_frm.set_intro("");
	if(doc.__islocal) {
		cur_frm.set_intro("First set the name and save the record.");
	}
	else {
		cur_frm.set_intro("Attach files / urls and add in table.");
	}
}