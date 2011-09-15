cur_frm.cscript['Export Report'] = function(doc, cdt, cdn) {
	$c_obj_csv(make_doclist(cdt, cdn), 'get_report_data', '');
}
