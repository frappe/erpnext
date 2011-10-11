// common partner functions
// =========================

/*
// make shipping list body
// ------------------------
cur_frm.cscript.make_sl_body = function(){
	cur_frm.fields_dict['Shipping HTML'].wrapper.innerHTML = '';
	cur_frm.shipping_html = $a(cur_frm.fields_dict['Shipping HTML'].wrapper,'div');
}
*/

// make history list body
// -----------------------
cur_frm.cscript.make_hl_body = function(){
	cur_frm.fields_dict['History HTML'].wrapper.innerHTML = '';
	cur_frm.history_html = $a(cur_frm.fields_dict['History HTML'].wrapper,'div');
}


/*
// set shipping list message
// --------------------------
cur_frm.cscript.set_sl_msg = function(doc){
	cur_frm.shipping_html.innerHTML = 'Shipping Address Details will appear only when you save the ' + doc.doctype.toLowerCase();
}
*/
/*
// set history list message
// -------------------------
cur_frm.cscript.set_hl_msg = function(doc){
	cur_frm.history_html.innerHTML= 'History Details will appear only when you save the ' + doc.doctype.toLowerCase();
}
*/


/*
// make shipping address
// -------------
cur_frm.cscript.make_shipping_address = function(doc, dt, dn){
  	cur_frm.shipping_html.innerHTML = '';

	var dsn = cur_frm.doc.customer_name;
	var dsa = cur_frm.doc.address;
	cl = new AddressList(cur_frm.shipping_html,dt,dn,dsn,dsa);
}
*/


// make history
// -------------
cur_frm.cscript.make_history = function(doc,dt,dn){
	cur_frm.history_html.innerHTML = '';
	cur_frm.cscript.make_history_list(cur_frm.history_html,doc);
}

// make history list
// ------------------
cur_frm.cscript.make_history_list = function(parent,doc){

	var sel = $a(parent,'select');
	
	var ls = ['Select Transaction..'];
	for(d in cur_frm.history_dict){
		ls.push(d);
	}
	
	add_sel_options(sel,ls,'Select..');
	
	var body = $a(parent,'div');
	body.innerHTML = '<div class="help_box">Please select a transaction type to see History</div>';
	
	sel.body = body;
	sel.doc = doc;
	
	sel.onchange = function(){
		for(d in cur_frm.history_dict){
			if(sel_val(this) == d){
				this.body.innerHTML = '';
				eval(cur_frm.history_dict[d]);
				return;
			}
			else{
				// pass
			}
		}
	}
}

// run list
// ---------
cur_frm.cscript.run_list = function(lst,parent,q,q_max,doc,dn,nm){
	
	parent.innerHTML = '';
	$dh(parent);
	
	lst.doc = doc;
	lst.dn = dn;
	lst.nm = nm;
	lst.page_len = 10;
	
	lst.get_query = function(){
		this.query = q;
		this.query_max = q_max;
	}
	
	lst.make(parent);
	lst.run();
	
	lst.onrun = function(){
		$ds(parent);
		if(!this.has_data()){
			parent.innerHTML = '';
			var dv = $a(parent,'div','help_box');
			$a(dv,'span').innerHTML = "No " + this.dn + " found. ";
			
			var lbl = 'Create the <b>first</b> ' + this.dn + ' for ' + this.doc.name;
			var sp = $a(dv,'span');
			sp.nm = this.nm;
			$(sp).html(lbl).addClass('link_type').click(function(){ newdoc(this.nm); });
		}
	}
}


// get sates on country trigger
// -----------------------------
cur_frm.cscript.get_states=function(doc,dt,dn){
   $c('runserverobj', args={'method':'check_state', 'docs':compress_doclist([doc])},
    function(r,rt){
      if(r.message) {
        set_field_options('state', r.message);
      }
    }  
  );

}

cur_frm.cscript.country = function(doc, dt, dn) {
  cur_frm.cscript.get_states(doc, dt, dn);
}

// territory help - cutsomer + sales partner
// -----------------------------------------
cur_frm.cscript.TerritoryHelp = function(doc,dt,dn){
  var call_back = function(){

    var sb_obj = new SalesBrowser();        
    sb_obj.set_val('Territory');
  }
  loadpage('Sales Browser',call_back);
}

// get query select Territory
// ---------------------------
if(cur_frm.fields_dict['territory']){
	cur_frm.fields_dict['territory'].get_query = function(doc,dt,dn) {
		return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
	}
}


// =======================================================================================================

// contact list
// --------------
ContactList = function(parent,dt,dn,dsn){
	
	var me = this;
	
	this.dt = dt;
	this.dn = dn;
	this.dsn = dsn ? dsn : dn;

	this.wrapper = $a(parent,'div');
	me.get_list();
}

// add contact
// ------------
ContactList.prototype.add_contact = function(){
	var me = this;
	
	// onload - set default values
	var cont = LocalDB.create('Contact');

	var c = locals['Contact'][cont];
	
	if(me.dt == 'Customer')	{
		c.is_customer = 1;
		c.customer = me.dn;
		c.customer_name = me.dsn;
	}
	else if(me.dt == 'Supplier'){
		c.is_supplier = 1;
		c.supplier = me.dn;
		c.supplier_name = me.dsn;
	}
	else if(me.dt == 'Sales Partner'){
		c.is_sales_partner = 1;
		c.sales_partner = me.dn;
		//c.sales_partner_name = me.dsn;
	}
	
	loaddoc('Contact',c.name);
}

// get contact list
// -----------------
ContactList.prototype.get_list = function(){
	var me = this;
	
	me.make_list();
	
	var dt = me.dt.toLowerCase().split(' ').join('_');
	
	// build query
	me.lst.get_query = function(){
		this.query = repl("select name, first_name, last_name, concat_ws(' ', first_name, last_name), email_id, contact_no, department, designation, is_primary_contact, has_login, disable_login from tabContact where %(dt)s = '%(dn)s' and docstatus != 2",{'dt':dt, 'dn':me.dn});

		this.query_max = repl("select count(name) from tabContact where %(dt)s = '%(dn)s' and docstatus != 2",{'dt':dt, 'dn':me.dn});
	}
	
	// render list ui
	me.lst.show_cell = function(cell,ri,ci,d){
		me.render_list(cell,ri,ci,d);
	}
	
	// run query
	me.lst.run();
	
	// onrun
	me.lst.onrun = function(){
		if(!this.has_data()){
			this.rec_label.innerHTML = '';
			
			$a(this.rec_label,'span').innerHTML = "You do not have any contact. ";
			$($a(this.rec_label,'span')).html('Add a new contact').addClass('link_type').click(function(){ me.add_contact(); });
			
			$dh(this.results);
		}
		else{
			$ds(this.results);
		}
	}	
}

// make list
// -----------
ContactList.prototype.make_list = function(){
	var me = this;
	
	var l = new Listing();
	l.colwidths = ['5%','30%','30%','20%','20%'];
	l.colnames = ['Sr.','Contact Name','Email Id','Contact No', 'Action'];
	l.page_len = 10;
  
	me.lst = l;
	
	l.make(me.wrapper);
	
	// Add contact button
	me.add_btn = $btn(l.btn_area,'+ Add Contact', function(){ me.add_contact();}, {fontWeight:'bold'});
}

// make contact cell
// ------------------
ContactList.prototype.render_list = function(cell,ri,ci,d){
	var me = this;

	// name
	if(ci == 0){
		var nm = $a($a(cell,'div'),'span','',{cursor:'pointer'});
		nm.innerHTML = d[ri][3];
		nm.id = d[ri][0];
		
		nm.onclick = function(){
			loaddoc('Contact', this.id);
			
			// on save callback - refresh list
		}

		// department and designation
		var des = d[ri][7] ? d[ri][7] : '';
		var dep = d[ri][6] ? d[ri][6] : '';
		
		var sp = $a(cell,'div','comment');
		sp.innerHTML = des + (dep ? (', ' + dep) : ''); 
	}
	
	// email id, contact no, department, designation
	// -----------------------------------------------------
	if(ci == 1) cell.innerHTML = d[ri][4] ? d[ri][4] : '-';
	if(ci == 2) cell.innerHTML = d[ri][5] ? d[ri][5] : '-';
	
	// actions
	// --------------------------------------
	if(ci== 3) me.make_actions(cell,ri,ci,d);
}

// make actions
// ---------------
ContactList.prototype.make_actions = function(cell,ri,ci,d){
	var me = this;
	
	var tab = make_table(cell,1,2,'100%',['40%','60%']);

	// Edit and Delete
	var t = make_table($td(tab,0,0),1,2);
	
	var edit = $a($td(t,0,0),'div','wn-icon ic-doc_edit');
	$(edit).click(function(){ loaddoc('Contact',d[ri][0]); });
	
	edit.setAttribute('title','Edit');

// Below code should be uncommented once customer/venodr invitation process is stable
// ===========================================================================
/* 
	var del = $a($td(t,0,1),'div','wn-icon ic-trash');
	$(del).click(function(){ me.delete_contact(d[ri][0],d[ri][4]) });

	set_custom_tooltip(del, 'Delete');
	
	//  Invite, Enable and Disable - Integrate after gateway logic incorporated

	if(d[ri][9] == 'Yes')	{
		if(d[ri][10] == 'Yes'){
			var enb = $a($td(tab,0,1),'div','wn-icon ic-checkmark');
			$(enb).click(function(){ me.enable_login(d[ri][0], d[ri][4]); });
		}
		else{
			var dsb = $a($td(tab,0,1),'div','wn-icon ic-delete');
			$(dsb).click(function(){ me.disable_login(d[ri][0], d[ri][4]) });
		}
	}
	else{
		var inv = $a($td(tab,0,1),'div','wn-icon ic-mail');
		$(inv).click(function(){ me.invite_contact(d[ri][0], d[ri][4], d[ri][1], d[ri][2]) });
	}*/
}

// enable login
// ----------------------------------------------------------
ContactList.prototype.enable_login = function(id, email_id){
	var me = this;
	
	var callback = function(r,rt){
		me.get_list();
		
		if(!r.exc) msgprint('Login for contact enabled',1);
		else errprint(r.exc);
	}
	
	var args = {};
	args.contact = id;
	args.email = email_id;
	
	$c_obj('Contact Control','enable_login',JSON.stringify(args),callback);
}

// disable login
// -------------------------------------------------------------
ContactList.prototype.disable_login = function(id, email_id){
	var me = this;
	
	var callback = function(r,rt){
		me.get_list();
		
		if(!r.exc) msgprint('Login for contact disabled',1);
		else errprint(r.exc);
	}

	var args = {};
	args.contact = id;
	args.email = email_id;
		
	$c_obj('Contact Control','disable_login',JSON.stringify(args),callback);
}

// delete contact
// -----------------
ContactList.prototype.delete_contact = function(id,email_id,has_login){
	var me = this;
	
	var callback = function(r,rt){
		me.get_list();
		
		if(!r.exc) msgprint('Contact deleted successfully');
		else errprint(r.exc);
	}
	
	var args = {};
	args.contact = id;
	args.email = email_id;
	args.has_login = has_login;
	
	$c_obj('Contact Control','delete_contact',JSON.stringify(args),callback);
}

// invite user
// --------------------------------------------------------
ContactList.prototype.invite_contact = function(id,email_id,first_name,last_name){
	var me = this;

	if(!email_id){
		msgprint("Please add email id and save the contact first. You can then invite contact to view transactions.")
	}
	else{
		var callback = function(r,rt){
			if(!r.exc) msgprint('Invitation sent');
			else errprint(r.exc);
		}
	
		var args = {
			'contact' : id,
			'email' : email_id,
			'first_name' : first_name ? first_name : '',
			'last_name' : last_name ? last_name : '',
			'usert_type' : 'Partner'
		};
		
		$c_obj('Contact Control','invite_contact',JSON.stringify(args),callback);	
	}
}


// address list
// --------------
AddressList = function(parent,dt,dn,dsn,dsa){
	
	var me = this;
	
	this.dt = dt;
	this.dn = dn;
	this.dsn = dsn ? dsn : dn;
        this.dsa = dsa ? dsa : '';

	this.wrapper = $a(parent,'div');
	me.get_addr_list();
}


// add contact
// ------------
AddressList.prototype.add_address = function(){
	var me = this;
	
	// onload - set default values
	var addr = LocalDB.create('Shipping Address');

	var a = locals['Shipping Address'][addr];
	
	a.customer = me.dn;
	a.customer_name = me.dsn;
        a.customer_address = me.dsa;	
	loaddoc('Shipping Address',a.name);
}


// get address list
// -----------------
AddressList.prototype.get_addr_list = function(){
	var me = this;
	
	me.make_addr_list();
	
	var dt = me.dt.toLowerCase().split(' ').join('_');
	
	// build query
	me.lst.get_query = function(){
		this.query = repl("select name, ship_to, shipping_address, is_primary_address, shipping_details from `tabShipping Address` where %(dt)s = '%(dn)s' and docstatus != 2",{'dt':dt, 'dn':me.dn});

		this.query_max = repl("select count(name) from `tabShipping Address` where %(dt)s = '%(dn)s'",{'dt':dt, 'dn':me.dn});
	}
	
	// render list ui
	me.lst.show_cell = function(cell,ri,ci,d){
		me.render_list(cell,ri,ci,d);
	}
	
	// run query
	me.lst.run();
	
	// onrun
	me.lst.onrun = function(){
		if(!this.has_data()){
			this.rec_label.innerHTML = '';
			
			$a(this.rec_label,'span').innerHTML = "You do not have any shipping address.";
			$($a(this.rec_label,'span')).html('Add a new address').addClass('link_type').click(function(){ me.add_address(); });
			
			$dh(this.results);
		}
		else{
			$ds(this.results);
		}
	}	
}


// make list
// -----------
AddressList.prototype.make_addr_list = function(){
	var me = this;
	
	var l = new Listing();
	l.colwidths = ['5%', '15%', '25%','10%','35%','10%'];
	l.colnames = ['Sr.', 'Ship To', 'Shipping Address','Primary Address', 'Shipping Details', 'Action'];
    l.page_len = 10;
  
	me.lst = l;
	
	l.make(me.wrapper);
	
	// Add address button
	me.add_btn = $btn(l.btn_area,'+ Add Address', function(){ me.add_address();}, {fontWeight:'bold'});
}



// make address cell
// ------------------
AddressList.prototype.render_list = function(cell,ri,ci,d){
	var me = this;

	// name
	if(ci == 0){
		var nm = $a($a(cell,'div'),'span','',{cursor:'pointer'});
		nm.innerHTML = d[ri][1];
		nm.id = d[ri][0];
		
		nm.onclick = function(){
			loaddoc('Shipping Address', this.id);
		}
	}
	
	// shipping address, primary address, shipping details
	// ----------------------------------------------------
	if(ci == 1) cell.innerHTML = d[ri][2] ? d[ri][2] : '-';
	if(ci == 2) cell.innerHTML = d[ri][3] ? d[ri][3] : '-';
	if(ci == 3) cell.innerHTML = d[ri][4] ? d[ri][4] : '-';
	
	// actions
	// --------------------------------------
	if(ci== 4) me.make_actions(cell,ri,ci,d);
}

// make actions
// ---------------
AddressList.prototype.make_actions = function(cell,ri,ci,d){
	var me = this;
	
	var tab = make_table(cell,1,2,'100%',['40%','60%']);

	// Edit and Delete
	var t = make_table($td(tab,0,0),1,2);
	
	var edit = $a($td(t,0,0),'div','wn-icon ic-doc_edit');
	$(edit).click(function(){ loaddoc('Shipping Address',d[ri][0]); });
	
	edit.setAttribute('title','Edit');
}
