$import(Contact Control)

cur_frm.cscript.onload = function(doc,dt,dn){

	// history doctypes and scripts
	cur_frm.history_dict = {
		'Purchase Order' : 'cur_frm.cscript.make_po_list(this.body, this.doc)',
		'Purchase Receipt' : 'cur_frm.cscript.make_pr_list(this.body, this.doc)',
		'Purchase Invoice' : 'cur_frm.cscript.make_pi_list(this.body, this.doc)'
	}
	
	// make contact, history list body
	//cur_frm.cscript.make_cl_body();
	cur_frm.cscript.make_hl_body();
}

cur_frm.cscript.refresh = function(doc,dt,dn) {
  if(sys_defaults.supp_master_name == 'Supplier Name')
    hide_field('naming_series');
  else
    unhide_field('naming_series'); 
    
  if(doc.__islocal){
    	hide_field(['Address HTML','Contact HTML']); 
  		//if(doc.country) cur_frm.cscript.get_states(doc,dt,dn);  	
		// set message
		//cur_frm.cscript.set_cl_msg(doc);
		//cur_frm.cscript.set_hl_msg(doc);
  }
  else{
	  	unhide_field(['Address HTML','Contact HTML']);
		// make lists
		cur_frm.cscript.make_address(doc,dt,dn);
		cur_frm.cscript.make_contact(doc,dt,dn);
		cur_frm.cscript.make_history(doc,dt,dn);  	
  }
}

cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new wn.widgets.Listing({
			parent: cur_frm.fields_dict['Address HTML'].wrapper,
			page_length: 2,
			new_doctype: "Address",
			new_doc_onload: function(dn) {
				ndoc = locals["Address"][dn];
				ndoc.supplier = cur_frm.doc.name;
				ndoc.supplier_name = cur_frm.doc.supplier_name;
				ndoc.address_type = 'Office';								
			},		
			new_doc_onsave: function(dn) {				
				cur_frm.address_list.run()
			},	
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where supplier='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_address desc"
			},
			as_dict: 1,
			no_results_message: 'No addresses created',
			render_row: function(wrapper, data) {
				$(wrapper).css('padding','5px 0px');
				var link = $ln(wrapper,cstr(data.name), function() { loaddoc("Address", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name
				
				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_address ? '[Primary]' : '') + (data.is_shipping_address ? '[Shipping]' : ''));
				$a(wrapper,'div','',{marginTop:'5px', color:'#555'}, 
					(data.address_line1 ? data.address_line1 + '<br />' : '') + 
					(data.address_line2 ? data.address_line2 + '<br />' : '') + 
					(data.city ? data.city + '<br />' : '') + 
					(data.state ? data.state + ', ' : '') + 
					(data.country ? data.country  + '<br />' : '') + 
					(data.pincode ? 'Pincode: ' + data.pincode + '<br />' : '') + 
					(data.phone ? 'Phone: ' + data.phone + '<br />' : '') + 
					(data.fax ? 'Fax: ' + data.fax + '<br />' : '') + 
					(data.email_id ? 'Email: ' + data.email_id + '<br />' : ''));			
			}
		});
	}
	cur_frm.address_list.run();
}

cur_frm.cscript.make_contact = function() {
	if(!cur_frm.contact_list) {
		cur_frm.contact_list = new wn.widgets.Listing({
			parent: cur_frm.fields_dict['Contact HTML'].wrapper,
			page_length: 2,
			new_doctype: "Contact",
			new_doc_onload: function(dn) {
				ndoc = locals["Contact"][dn];
				ndoc.supplier = cur_frm.doc.name;
				ndoc.supplier_name = cur_frm.doc.supplier_name;
			},
			new_doc_onsave: function(dn) {				
				cur_frm.contact_list.run()
			},
			get_query: function() {
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where supplier='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: 'No contacts created',
			render_row: function(wrapper, data) {
				$(wrapper).css('padding', '5px 0px');
				var link = $ln(wrapper, cstr(data.name), function() { loaddoc("Contact", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name

				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_contact ? '[Primary]' : ''));
				$a(wrapper,'div', '',{marginTop:'5px', color:'#555'}, data.first_name + (data.last_name ? ' ' + data.last_name + '<br />' : '<br>') + (data.phone ? 'Tel: ' + data.phone + '<br />' : '') + (data.mobile_no ? 'Mobile: ' + data.mobile_no + '<br />' : '') + (data.email_id ? 'Email: ' + data.email_id + '<br />' : '') + (data.department ? 'Department: ' + data.department + '<br />' : '') + (data.designation ? 'Designation: ' + data.designation + '<br />' : ''));
			}
		});
	}
	cur_frm.contact_list.run();
}

// make purchase order list
cur_frm.cscript.make_po_list = function(parent, doc){
	var lst = new Listing();
	lst.colwidths = ['5%','25%','20%','25%','25%'];
	lst.colnames = ['Sr.','Id','Status','PO Date','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Currency'];
	lst.coloptions = ['','Purchase Order','','','',''];

	var q = repl("select name,status,transaction_date, grand_total from `tabPurchase Order` where supplier='%(sup)s' order by transaction_date desc", {'sup':doc.name});
	var q_max = repl("select count(name) from `tabPurchase Order` where supplier='%(sup)s'", {'sup':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Purchase Order','Purchase Order');
}

// make purchase receipt list
cur_frm.cscript.make_pr_list = function(parent,doc){
	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','20%','15%','20%'];
	lst.colnames = ['Sr.','Id','Status','Receipt Date','% Billed','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Currency','Currency'];
	lst.coloptions = ['','Purchase Receipt','','','',''];
	
	var q = repl("select name,status,transaction_date,per_billed,grand_total from `tabPurchase Receipt` where supplier='%(sup)s' order by transaction_date desc", {'sup':doc.name});
	var q_max = repl("select count(name) from `tabPurchase Receipt` where supplier='%(sup)s'", {'sup':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Purchase Receipt','Purchase Receipt');
}

// make purchase invoice list
cur_frm.cscript.make_pi_list = function(parent,doc){
	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','20%','15%','20%'];
	lst.colnames = ['Sr.','Id','Posting Date','Credit To','Bill Date','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Currency','Currency'];
	lst.coloptions = ['','Payable Voucher','','','',''];

	var q = repl("select name, posting_date, credit_to, bill_date, grand_total from `tabPayable Voucher` where supplier='%(sup)s' order by posting_date desc", {'sup':doc.name});
	var q_max = repl("select count(name) from `tabPayable Voucher` where supplier='%(sup)s'", {'sup':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Purchase Invoice','Payable Voucher');	
}
