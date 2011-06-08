cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.customer) cur_frm.add_fetch('customer', 'customer_name', 'customer_name');
	if(doc.supplier) cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name');
}

