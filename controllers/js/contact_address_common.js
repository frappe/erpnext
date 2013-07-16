cur_frm.cscript.onload = function(doc, cdt, cdn) {	
	cur_frm.add_fetch('customer', 'customer_name', 'customer_name');
	cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name');

	cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;
	cur_frm.fields_dict.supplier.get_query = erpnext.utils.supplier_query;
	
	if(cur_frm.fields_dict.lead) {
		cur_frm.fields_dict.lead.get_query = erpnext.utils.lead_query;
		cur_frm.add_fetch('lead', 'lead_name', 'lead_name');
	}
	
	if(doc.__islocal) {
		var last_route = wn.route_history.slice(-2, -1)[0];
		if(last_route && last_route[0]==="Form") {
			if(["Customer", "Quotation", "Sales Order", "Sales Invoice", "Delivery Note",
				"Installation Note", "Opportunity", "Customer Issue", "Maintenance Visit",
				"Maintenance Schedule"]
				.indexOf(last_route[1])!==-1) {
				var refdoc = wn.model.get_doc(last_route[1], last_route[2]);

				if(refdoc.doctype == "Quotation" ? refdoc.quotation_to=="Customer" : true) {
					cur_frm.set_value("customer", refdoc.customer || refdoc.name);
					cur_frm.set_value("customer_name", refdoc.customer_name);
					if(cur_frm.doc.doctype==="Address")
						cur_frm.set_value("address_title", cur_frm.doc.customer_name);
				}
			}
			if(["Supplier", "Supplier Quotation", "Purchase Order", "Purchase Invoice", "Purchase Receipt"]
				.indexOf(last_route[1])!==-1) {
				var refdoc = wn.model.get_doc(last_route[1], last_route[2]);
				cur_frm.set_value("supplier", refdoc.supplier || refdoc.name);
				cur_frm.set_value("supplier_name", refdoc.supplier_name);
				if(cur_frm.doc.doctype==="Address")
					cur_frm.set_value("address_title", cur_frm.doc.supplier_name);
			}
			if(["Lead", "Quotation"]
				.indexOf(last_route[1])!==-1) {
				var refdoc = wn.model.get_doc(last_route[1], last_route[2]);
				
				if(refdoc.doctype == "Quotation" ? refdoc.quotation_to=="Lead" : true) {
					cur_frm.set_value("lead", refdoc.lead || refdoc.name);
					cur_frm.set_value("lead_name", refdoc.customer_name || refdoc.company_name || refdoc.lead_name);
					if(cur_frm.doc.doctype==="Address")
						cur_frm.set_value("address_title", cur_frm.doc.lead_name);
				}
			}
		}
	}
}
