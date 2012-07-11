cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.toggle_fields('year', doc.__islocal);
	cur_frm.enable_fields('year_start_date', doc.__islocal)
}
