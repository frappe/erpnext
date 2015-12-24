cur_frm.cscript.refresh = function(doc, dt, dn){
	if(!doc.__islocal){
		var df = frappe.meta.get_docfield(doc.doctype, "gateway", doc.name);
		df.read_only = 1;
	}
}