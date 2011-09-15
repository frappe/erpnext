pscript['onload_Setup Wizard'] = function()
{   

  // header and toolbar
  var h = new PageHeader('setup_wizard_wrapper','Setup Wizard','All important setup items in one place');

  pscript.setup_wizard_callback();
}

// ==================================================================================================

pscript.setup_wizard_callback = function(){
    var items = {};
    items['Customer'] = new pscript.Setup_Wizard_Obj('Customer', 'customer_name', 0, '', 'Customer', 'Manage your customers',1);
    items['Supplier'] = new pscript.Setup_Wizard_Obj('Supplier', 'supplier_name', 0, '', 'Supplier', 'Manage your supplier',1);
    items['Item'] = new pscript.Setup_Wizard_Obj('Item', 'item_name', 0, '', 'Item', 'Create your items',1);
    //items['Customer Group'] = new pscript.Setup_Wizard_Obj('Customer Group', 'group_name', 0, '', 'Customer Group', 'Organizes your customers for better analysis');
    items['Price List'] = new pscript.Setup_Wizard_Obj('Price List', 'price_list_name', 0, '', 'Price List', 'Helps you maintain different prices for different customers, currencies etc.');
    items['Supplier Type'] = new pscript.Setup_Wizard_Obj('Supplier Type', 'supplier_type', 0, '', 'Supplier Type', 'Organizes your suppliers for better analysis');
    //items['Item Group'] = new pscript.Setup_Wizard_Obj('Item Group', 'group_name', 0, '', 'Item Group', 'Organizes your items for better analysis');
    items['UoM'] = new pscript.Setup_Wizard_Obj('UOM', 'uom_name', 0, '', 'UOM', 'Maintain multiple Units of Measure (UOM)');
    items['Warehouse Type'] = new pscript.Setup_Wizard_Obj('Warehouse Type', 'warehouse_type', 0, '', 'Warehouse Type', 'Define types of warehouses');
    items['Warehouse'] = new pscript.Setup_Wizard_Obj('Warehouse', 'warehouse_name', 'warehouse_type', 'Warehouse Type', 'Warehouse', 'Manage stock across different warehouses');
    items['Print Heading'] = new pscript.Setup_Wizard_Obj('Print Heading', 'print_heading', 'transaction', 'Transaction', 'Print Heading', 'Define print heading for various transaction.');
    items['Warehouse Type'].onmake = function(){
       items['Warehouse'].refresh_select('warehouse_type', 'Warehouse Type', 'Warehouse');
    }
    items['Print Heading'].onmake = function(){
       items['Print Heading'].refresh_select('transaction', 'Transaction', 'Print Heading');
    }
}

// ==================================================================================================
pscript.Setup_Wizard_Obj = function(lbl, name_field, opt_fieldname, opt_field_tbl, dt, desc, important) 
{
    this.lbl = lbl;
    this.make_body(lbl, important);
    if(lbl != 'Item')
      this.make_input(name_field);
    if(opt_fieldname){
      this.make_select(opt_fieldname, opt_field_tbl, dt);
    }
   
    this.show_description(desc);
    this.make_button();
    this.create_doc_link(dt);

}

pscript.Setup_Wizard_Obj.prototype.make_body = function(lbl, important) {
    var wrapper = $a($i('setup_wizard_wrapper'), 'div', '', {padding:'8px', borderBottom: '1px solid #AAA'});
    if(important)$y(wrapper, {backgroundColor:'#FFD'});
    this.tab = make_table(wrapper,1,3,'90%',['20%','50%','30%'], {padding:'2px 0px', verticalAlign:'middle'});
    this.desc_area = $a(wrapper,'div','comment');
    
    $td(this.tab,0,0).innerHTML = lbl.bold();
}

pscript.Setup_Wizard_Obj.prototype.make_input = function(name_field){
    this.input = $a_input($td(this.tab,0,1), 'text');
    this.name_field = name_field;
}

pscript.Setup_Wizard_Obj.prototype.make_select = function(fn, ft, dt){
    this.select = $a($td(this.tab,0,1), 'select', '', {width:'120px', marginLeft:'8px'});
    this.opt_field = fn;
    this.sel_field = 'Select ' + ft + '...';
    this.refresh_select(fn, ft, dt);
}                

pscript.Setup_Wizard_Obj.prototype.refresh_select = function(fn, ft, dt){
  var me = this;
  if(ft == 'Transaction'){
    empty_select(me.select);
    add_sel_options(me.select, ['Select Transaction ...','Purchase Order','Sales Order','Service Order','Purchase Receipt','Delivery Note','Receivable Voucher','Payable Voucher','Journal Voucher']);
  }
  else{
    $c_obj('Setup Wizard Control', 'get_master_lists','', function(r,rt){
      var ft_lst = [];
      if(r.message) ft_lst = r.message;
      ft_lst.push('Select Warehouse Type ...');
      empty_select(me.select);
      add_sel_options(me.select, ft_lst.reverse(), 'Warehouse Type');
    });
  }
}  
 
pscript.Setup_Wizard_Obj.prototype.make_button = function(){   
    var me = this;

    var create = $a($td(this.tab,0,1), 'button', '', {marginLeft:'8px'});
    create.innerHTML = 'Create';
    
    create.onclick = function(){
        me.create_record(this);
    }
}

// show description
pscript.Setup_Wizard_Obj.prototype.show_description=function(desc){ 
    this.desc_area.innerHTML = desc;
}

// create link to show listing of all records
pscript.Setup_Wizard_Obj.prototype.create_doc_link = function(doc_link){  
    this.obj_link = $a($td(this.tab,0,2), 'span', 'link_type',{marginLeft:'8px'});
    this.obj_link.innerHTML = 'View ' + doc_link + ' list';
    this.dt = doc_link;

    this.obj_link.onclick = function(){
      if(doc_link == 'Customer') doc_lst = 'customer_group'+NEWLINE+'country';
      else if(doc_link == 'Supplier') doc_lst = 'supplier_type'+NEWLINE+'supplier_status'+NEWLINE+'company';
      else if(doc_link == 'Item') doc_lst = 'item_group'+NEWLINE+'description';
        
      if(doc_link == 'Customer' || doc_link == 'Supplier' || doc_link == 'Item')
        loaddocbrowser(doc_link,doc_link, doc_lst);
      else
        loaddocbrowser(doc_link);
    }
}    
pscript.Setup_Wizard_Obj.prototype.create_record = function(cur_obj)
{   
    var me = this;
    if(me.lbl == 'Item'){ me.create_master_rec(); }
    else{
      if(this.input.value) { //check for input value
        
        if (this.select && (this.sel_field == this.select.value)){ //check for value is selected or not
          alert('Please select '+this.select.value);  
          this.input.value = '';
        }
        else{
          args = {};
          args['Doctype'] = this.dt;
          if(strip(this.input.value) == ''){ alert("Please enter proper name."); me.input.value = '';}
          else{
            if(me.lbl == 'Customer' || me.lbl == 'Supplier'){ this.create_master_rec(); }
            else{
              args[this.name_field] = this.input.value;
              args[this.opt_field] = this.opt_field ? this.select.value : '';
              
              $c_obj('Setup Wizard Control', 'create_record', JSON.stringify(args), function(r,rt){        
                alert(r.message);
                me.input.value = '';
                if(me.onmake) me.onmake();  
              });
            }
          }
        }
      }
      else
        alert("Please enter " +this.dt);
    }
}

pscript.Setup_Wizard_Obj.prototype.create_master_rec = function(){
  var me = this;
  var fn = function(new_docname) {
    var new_doc = locals[me.lbl][new_docname];
    if(me.lbl == 'Customer')
      new_doc.customer_name = me.input.value;
    else if(me.lbl == 'Supplier')
      new_doc.supplier_name = me.input.value;
  }
  new_doc(me.lbl, fn);
  
}