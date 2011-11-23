pscript.onload_Setup = function() {
  var parent = $i('setup_div');
  add_space_holder(parent);

  var callback = function(r,rt){

    // header
    parent.page_head = new PageHeader(parent,'Setup');
    
    // sections
    var setup_data = new SetupData(r.message);
    pscript.setup_make_sections(setup_data);
    
    remove_space_holder();
  }
  $c_obj('Setup Wizard Control','get_country','',callback);  
}

pscript.setup_set_height = function() {
  var parent = $i('setup_div');
  $y(parent.tray.body, {height: get_window_height() - parent.page_head.wrapper.offsetHeight + 'px', overflow:'auto'})
}

// Make sections
// ===================================================

pscript.setup_make_sections = function(setup_data) {
  var parent = $i('setup_div');
  parent.tray = new TrayPage(parent)

  // list of setup data
  var lst = [setup_data.system, setup_data.general, setup_data.accounts, setup_data.selling, setup_data.buying, setup_data.stock, setup_data.hr, setup_data.maintenance, setup_data.production];

  for(var s=0; s<lst.length; s++){
    var lbl = keys(lst[s])[0];

    var ti = parent.tray.add_item(lbl, null, null, 1)
    new SetupItem(ti.body, lbl, lst[s][lbl]);

    if(s==0) ti.expand();
  }
  
  setTimeout(pscript.setup_set_height, 100);
  resize_observers.push(pscript.setup_set_height);
}

// Setup Item
// ===================================================
SetupItem = function(parent, lbl, link_list) {
  this.icons = {'System':'back_img Setup', 'General':'back_img Home', 'Accounts':'back_img Accounts', 'Selling':'back_img Selling', 'Stock':'back_img Stock', 'Buying':'back_img Buying', 'Maintenance':'back_img Maintenance', 'Production':'back_img Production', 'HR':'back_img HR'};
  this.make_item_body(parent, lbl, link_list);
}


// Make body for item in setup wizard
// ===================================================
SetupItem.prototype.make_item_body = function(parent, lbl, link_list){
  // item link area
  this.link_area = parent;
  this.render_item_body(lbl, link_list);
}


// Render item body
// ===================================================
SetupItem.prototype.render_item_body = function(lbl, link_list) {
  var me = this;
  // set item header

  link_list.sort(function(a, b) { return a[0] > b[0]; });

  // show links for item
  for(var i=0; i<link_list.length; i++){
    var wrapper = $a(this.link_area, 'div','',{marginBottom:'4px', padding:'2px'});
    $(wrapper).hover(
      function() { $y(this,{backgroundColor:'#EEF'}) }
      ,function() { $y(this,{backgroundColor:''}) }
    )
    var tab = make_table($a(wrapper,'div'), 1, 2, '100%', [200/7+'%', 500/7+'%'])

    var dt= $a($td(tab,0,0), 'span', 'link_type');
    dt.innerHTML = link_list[i][0]; 
    dt.label = link_list[i][0];
    dt.arg = link_list[i][1]; 
    dt.nm = link_list[i][2];
    
    if(dt.arg == 1) dt.cn = link_list[i][3]; 
    else if(dt.arg == 2) dt.cb=link_list[i][3];
 
    // execute when link is clicked
    dt.onclick = function(){
      me.link_action(this)
    }
    
    // description
    $y($td(tab,0,1), {color:'#777'});
    $td(tab,0,1).innerHTML = link_list[i][4];
  }
}


// Execute when link is clicked
// ----------------------------
SetupItem.prototype.link_action = function(obj) {
  var me = this;
  var obj = obj;
  
  // if object links to a doc browser
  if(obj.arg == 1){
    if(in_list(profile.can_read, obj.nm)){
      if(obj.cn !='')
        loaddocbrowser(obj.nm, obj.nm, obj.cn);
      else
        loaddocbrowser(obj.nm);
    }
    else
      msgprint('No read permission',1);
  }
  
  // if obj links to a page
  else if(obj.arg == 2){
    me.show_page(obj);
  }
  
  // if object links to a single doctype
  else if(obj.arg == 3){
    newdoc(obj.nm);
  }
}


// Show page for corresponding link
// --------------------------------
SetupItem.prototype.show_page = function(obj) {
  var me = obj;
  var callback = function(r,rt)
  {
    if(r.message){
      if(me.cb == '')
        loadpage(me.nm);
      else
        show_chart_browser(me.nm,me.cb);    
    }
    else
      msgprint('No read permission',1);
  }
  $c_obj('Setup Wizard Control','get_page_lst',me.nm,callback);  
}


// Setup Data
// ======================================================================================================================================================= 
SetupData = function(cnty){

  // arg : 1 - Docbrowser, 2 - Page, 3 - DocType
  
  //[label, arg, name, callback/col_name, description]

  this.system = {'System':[['Global Defaults',3,'Manage Account','','Set global default values'],
    ['Manage Series',3,'Naming Series','','Manage numbering series for transactions'],
    ['Custom Field',1,'Custom Field','dt'+NEWLINE+'label'+NEWLINE+'fieldtype'+NEWLINE+'options','Add and manage custom fields on forms'],
    ['Email Settings',3,'Email Settings','','Outgoing email server and address'],
    ['Notification Settings',3,'Notification Control','','Automatic emails set at selected events'],
    ['Company',1,'Company','id'+NEWLINE+'is_active'+NEWLINE+'email','Manage list of companies'],
    ['Fiscal Year',1,'Fiscal Year','id'+NEWLINE+'company'+NEWLINE+'is_active'+NEWLINE+'year','Manage list of fiscal years'],
    ['Personalize',3,'Personalize','','Set your banner'],
    ['Manage Trash',2,'Trash','','Restore trashed items'],
    ['Import Data',2,'Import Data','','Import data from CSV files'],
    ['Manage Users',2,'My Company','','Add / remove users and manage their roles'],
    ['Web Forms',2,'Webforms','', 'Code to embed forms in yor website'],
    ['Permissions Manager',2,'Permission Engine','', 'Manage all permissions from one tool (beta)'],
    ['Property Setter',1,'Property Setter','', 'Customize properties of a Form (DocType) or Field'],
    ['Letter Head',1,'Letter Head','','Manage different letter heads for Prints'],
    ['SMS Settings',3,'SMS Settings','','Integrate your personalized SMS gateway which support http web service'],
    ['SMS Center',3,'SMS Center','','Send mass sms to your leads, contacts and partners'],
    ['Features Setup',3,'Features Setup','','Displays fields based on features selected']
  ]};

  
  this.general = {'General':[['Authorization Rule',1,'Authorization Rule','','Set rules based on amounts'],
    ['Print Heading',1,'Print Heading','','Manage headings for printing transactions'],
    ['Term',1,'Term','','Manage template of standard Terms for order / invoices etc'],
    ['Currency',1,'Currency','','Manage list of currencies'],
    ['Address',1,'Address','','Manage Address of customers, suplliers'],
    ['Country',1,'Country','','Country master'],
    ['State',1,'State','','State master'],
    ['Rename Tool',3,'Rename Tool','','Rename a record'],
    ['Bulk Rename Tool',3,'Bulk Rename Tool','','Rename multiple records at a time'],
    ['Activty Type',1,'Activity Type','','Types of activities that you can select in your Timesheet'],
    ['City',1,'City','','City master']]};
  
  this.selling = {'Selling':[['Customer Group',2,'Sales Browser','Customer Group','Manage customer categories'],
    ['Territory',2,'Sales Browser','Territory','Manage sales territories'],
    ['Customer',1,'Customer','customer_group'+NEWLINE+'country','Customer master'],
    ['Sales Person',2,'Sales Browser','Sales Person','Manage sales persons'],
    ['Sales Partner',1,'Sales Partner','', 'Manage sales partners'],
    ['Campaign',1,'Campaign','id'+NEWLINE+'campaign_name'+NEWLINE+'description','Manage sales / marketing campaigns'],
    ['Sales BOM',1,'Sales BOM','id'+NEWLINE+'is_active'+NEWLINE+'new_item_name'+NEWLINE+'description'+NEWLINE+'item_group','Manage Sales Bill of Material (Main item + accessories)'],
    ['Price List',1,'Price List','','Price list master']]};

  this.accounts = {'Accounts':[['Chart of Accounts',2,'Accounts Browser','Account','Manage chart of accounts'],
    ['Chart of Cost Centers',2,'Accounts Browser','Cost Center','Manage chart of cost centers'],
    ['POS Setting',1,'POS Setting','','Manage Point of Sales default Settings.']]};
    
  // if country = india; show india related doctypes
  //-------------------------------------------------
    
  if(cnty == 'India'){  
    var lst1 = [['TDS Rate Chart',1,'TDS Rate Chart','', 'TDS rate master'],['TDS Category',1,'TDS Category','id'+NEWLINE+'module','TDS categories']];
    for(var i =0; i<lst1.length;i++)      
      this.accounts['Accounts'].push(lst1[i]);
  }
  //--------------------------------------------------    
  
  var lst = [['Monthly Distribution',1,'Budget Distribution','id'+NEWLINE+'fiscal_year'+NEWLINE+'distribution_id','Manage budget distributions (seasonalities)'],
    ['Sales Other Charges',1,'Other Charges','','Manage your charge structures (taxes + charges) for sales'],
    ['Purchase Other Charges',1,'Purchase Other Charges','','Manage your charge structures (taxes + charges) for purchase'],
    ['Mode of Payment',1,'Mode of Payment','','Mode of payment master']];
             
  for(var i =0; i<lst.length;i++)
      this.accounts['Accounts'].push(lst[i]);
  
  this.stock = {'Stock':[['Item Group',2,'Sales Browser','Item Group','Manage item classifications'],
    ['Item',1,'Item','name'+NEWLINE+'item_group'+NEWLINE+'description','Item master'],
    ['Brand',1,'Brand','id'+NEWLINE+'description','Brand master'],
    ['Batch',1,'Batch','name'+NEWLINE+'start_date'+NEWLINE+'item'+NEWLINE+'expiry_date','Manage batches'],
    ['Price List',1,'Price List','','Price list master'],
    ['UOM',1,'UOM','','Unit of measure (UOM) master'],
    ['Warehouse Type',1,'Warehouse Type','','Warehouse classifications'],
    ['Warehouse',1,'Warehouse','','Warehouse master']]};
  
  this.buying = {'Buying':[['Supplier Type',1,'Supplier Type','','Manage supplier classifications'],
    ['Supplier',1,'Supplier','id'+NEWLINE+'supplier_type'+NEWLINE+'supplier_status'+NEWLINE+'company','Supplier master']]};
  
  this.maintenance = {'Maintenance':[['Serial No',1,'Serial No','item_code'+NEWLINE+'status'+NEWLINE+'pr_no'+NEWLINE+'delivery_note_no'+NEWLINE+'customer_name','Manage unique serial numbers for items'],
    ['Purpose of Service',1,'Purpose of Service','','Purpose of service master']]};
  
  this.production = {'Production':[['Bill of Materials',1,'Bill Of Materials','id'+NEWLINE+'item'+NEWLINE+'description'+NEWLINE+'operating_cost'+NEWLINE+'maintained_by','Muti-level bill of materials and operations'],
    ['Workstation',1,'Workstation','id'+NEWLINE+'workstation_name'+NEWLINE+'warehouse'+NEWLINE+'description','Workstation master']]};
  
  this.hr = {'HR':[['Department',1,'Department','','Company department master'],
    ['Designation',1,'Designation','','Company designation master'],
    ['Branch',1,'Branch','','Manage branches for your company'],
    ['Grade',1,'Grade','','Manage employee grades'],
    ['Employment Type',1,'Employment Type','','Manage types of employment'],
    ['Employee',1,'Employee','employee_name'+NEWLINE+'employment_type'+NEWLINE+'status'+NEWLINE+'branch'+NEWLINE+'designation'+NEWLINE+'department'+NEWLINE+'grade'+NEWLINE+'reports_to','Employee master'],
    ['Earning Type',1,'Earning Type','taxable'+NEWLINE+'exemption_limit','Types of salary earning master'],
    ['Deduction Type',1,'Deduction Type','','Types of salary deduction master'],
    ['Expense Type',1,'Expense Type','', 'Types of expense master'],
      
    ['Salary Structure',1,'Salary Structure','employee'+NEWLINE+'is_active'+NEWLINE+'fiscal_year'+NEWLINE+'from_date'+NEWLINE+'ctc'+NEWLINE+'total_earning'+NEWLINE+'total_deduction'+NEWLINE+'total','Salary structure template'],
    ['Holiday List',1,'Holiday List','fiscal_year','List of holidays'],
    ['Leave Type',1,'Leave Type','max_days_allowed'+NEWLINE+'is_carry_forward'+NEWLINE+'is_encash','Leave type master'],
    ['KRA Template',1,'KRA Template','','Template of Key Result Areas (KRAs)']]};
}
