cur_frm.cscript.refresh = function(doc) {	
	if (doc.docstatus) hide_field('Steps');
}

cur_frm.cscript['Download Template'] = function(doc, cdt, cdn) {
	$c_obj_csv(make_doclist(cdt, cdn), 'get_template', '');
}
