pscript['onload_Accounts Browser'] = function(){
  // if the user directly loads the page, ask to select the chart
  var parent = $i('ab_body');
  parent.innerHTML = 'Please select your chart: '
  var sel = $a(parent,'select');
  add_sel_options(sel, ['Account', 'Cost Center'], 'Account');
  var btn = $btn(parent, 'Go', function() { pscript.make_chart(sel_val(sel)); }, {marginTop:'8px'});
}

pscript.make_chart = function(b) {
  pscript.chart_type = b;
  $i('ab_header').innerHTML ='';
  $i('ab_body').innerHTML ='';

  //===============comment area========================================
  var comment = $a($i('ab_body'),'div','comment',{marginBottom:"8px"});
  comment.innerHTML = "Note: Explore and click on the tree node to add a new child";
  
  var select_area = $a('ab_body', 'div', '', {margin:'8px 0px'});
  
  //================== table body======================================  
  var ac_main_grid = make_table($i('ab_body'),1,2,'100%',['60%','40%'],{border:"0px", padding:"4px",tableLayout: "fixed", borderCollapse: "collapse"});
  $y($td(ac_main_grid,0,0),{border: "1px solid #dddddd", padding: "8px"});
  pscript.account_tree = $a($td(ac_main_grid,0,0),'div');
  $y($td(ac_main_grid,0,1),{border: "1px solid #DDD"});
  pscript.la = $a($td(ac_main_grid,0,1),'div');
  pscript.acc_period_bal = $a($td(ac_main_grid,0,1),'div');
  
  //=====================footer area ==================================
  if (pscript.chart_type == 'Account') {
    var footer = $a($i('ab_body'),'div','',{backgroundColor: "#FFD", padding: "8px", color: "#444", fontSize: "12px", marginTop: "14px"});
    
    var help1 = $a(footer,'span');
    help1.innerHTML = "<strong>Note:</strong> To create accounts for Customers and Suppliers, please create <a href='#Page/Selling'>Customer</a> and <a href='#Page/Buying'>Supplier</a>"
      + " Masters. This will ensure that the accounts are linked to your Selling and Buying Processes. The Account Heads for Customer and Supplier will automatically be created."
  }

  // header and toolbar
  // ------------------
  
  var h1 = 'Chart of '+pscript.chart_type+'s';
  if(pscript.chart_type == 'Account') var d = 'accounting';
  else var d = 'cost center';
  var desc = 'Manage multiple companies and the '+d+' structures of each company.';
  $i('ab_body').page_head = new PageHeader('ab_header',h1,desc);

  // select company
  // --------------
  var tab = make_table(select_area, 1, 2, null, [], {verticalAlign:'middle', padding: '2px'});
  $td(tab,0,0).innerHTML = 'Select Company'.bold();
  var sel = $a($td(tab,0,1),'select','',{width:'160px'});

  // set tree
  var set_tree = function() {
    if(pscript.ac_tree) {
      pscript.ac_tree.body.innerHTML = '';
    }
    pscript.make_ac_tree();
    var cn = sel_val(sel);
    var n = pscript.ac_tree.addNode(null, cn, null,pscript.ac_tree.std_onclick, pscript.ac_tree.std_onexp);
    n.rec = {}; 
    n.rec.name = 'Root Node'; 
    n.rec.account_name = cn;
    n.rec.cost_center_name = cn;
    pscript.set_ac_head('',n.rec);
    $ds(pscript.ac_head_area);
  }

  // select company
  add_sel_options(sel, ['Loading...']);
  var callback = function(r,rt) {    
    empty_select(sel); 
    add_sel_options(sel,r.message.cl,sys_defaults.company);    
    set_tree();
    sel.onchange = function() { set_tree(); }
  }
  $c_obj('GL Control', 'get_companies', '', callback);
  
  pscript.ab_company_sel = sel; 

  pscript.make_ac_head();
  pscript.make_group_area();
  pscript.make_ledger_area();
  pscript.make_new_acc_dialog();
  pscript.make_new_comp();
  pscript.make_new_cost_center_dialog();

}
//New company link
pscript.make_new_comp = function(){
  $i('ab_body').page_head.add_button('New Company', function() { new_doc('Company'); }, 0, 'ui-icon-plus');
}

pscript.make_ac_tree = function() {
  //var type= sel_val($i('chart_type'))
  var type= pscript.chart_type;
  var tree = new Tree(pscript.account_tree, '90%');
  pscript.ac_tree = tree;

  // on click
  tree.std_onclick = function(node) {

    
    pscript.cur_node = node;

    // show ledger
    pscript.set_ac_head(node.parent_account, node.rec,type);
  }

  // on expand
  tree.std_onexp = function(node) {
    if(node.expanded_once)return;
    $ds(node.loading_div);
    //set_ac_head
    var callback = function(r,rt) {

      $dh(node.loading_div);
      var n = tree.allnodes[r.message.parent_acc_name];

      var cl = r.message.cl;

      if(type=='Account'){
        for(var i=0;i<cl.length;i++) {
          var imgsrc=null;
          var has_children = true;
          if(cl[i].group_or_ledger=='Ledger') {
            var imgsrc = 'images/icons/page.gif';
            has_children = false;
          }
          var t = tree.addNode(n, cl[i].account_name, imgsrc,tree.std_onclick, has_children ? tree.std_onexp : null);
          t.rec = cl[i];
          t.parent_account = r.message.parent;
        }
      }
      else{
        for (var i=0;i<cl.length;i++){
          var imgsrc=null;
          var has_children = true;
          if(cl[i].group_or_ledger=='Ledger') {
            var imgsrc = 'images/icons/page.gif';
            has_children = false;
          }
          var t = tree.addNode(n, cl[i].cost_center_name, imgsrc,tree.std_onclick, has_children ? tree.std_onexp : null);
          t.rec = cl[i];
          t.parent_account = r.message.parent;
        }
      }
    }

    if (type=='Account'){
      var arg = [node.rec.name, node.rec.account_name, sel_val(pscript.ab_company_sel), pscript.chart_type];
    } else{
        var arg = [node.rec.name, node.rec.cost_center_name,sel_val(pscript.ab_company_sel), pscript.chart_type];
    }

    $c_obj('GL Control','get_cl',arg.join(','),callback);
  }
}

pscript.make_ac_head = function() {
  var div = $a(pscript.la,'div','ac_head');
  div.main_head = $a(div,'h3','',{padding:'4px', margin:'0px',backgroundColor:'#EEEEEE',borderBottom:'1px solid #AAAAAA'});
  
  div.sub_head1 = $a(div,'div');
  div.sub_head2 = $a(div,'div');
  
  div.balance_area = $a(div,'div');
  $a(div.balance_area,'span','sectionHeading').innerHTML = "Balance:";
  div.balance = $a(div.balance_area,'span','ac_balance');

  div.sub_head = $btn(div,'Edit',function() { loaddoc(this.dt, this.dn); });
  pscript.ac_head_area = div;
}

// Group / Ledger Area - set properties in the right column
//---------------------------------------------------------

pscript.set_ac_head = function(parent_account, r,type) {  
  var d = pscript.ac_head_area;  
  d.main_head.innerHTML = r.account_name;
  $ds(d.sub_head);
  $ds(d.balance_area);  
  
  var callback = function(r,rt) {
   dcc = r.message;
  }
  $c_obj('GL Control', 'get_company_currency', pscript.ab_company_sel.value, callback);	        
 
  if(r.name!='Root Node') {
    // Account group/ledger area
    if(type=='Account'){      
      d.sub_head.dt = 'Account'; d.sub_head.dn = r.name

      d.sub_head1.innerHTML = r.debit_or_credit + ' - ' + r.group_or_ledger;
      d.sub_head2.innerHTML = 'Group: ' + parent_account;
      if(r.group_or_ledger=='Ledger') {
        $ds(pscript.ledger_area);
        $ds(pscript.gl_rep);
        $dh(pscript.cc_rep);
        $dh(pscript.group_area);
      } else {
        $dh(pscript.ledger_area);
        $ds(pscript.group_area);
        $ds(pscript.acc_add_btn);
        $dh(pscript.cc_add_btn);
      }           
	  
	  var callback = function(r,rt) {
	   dcc = r.message;	   
	  }
	  $c_obj('GL Control', 'get_company_currency', pscript.ab_company_sel.value, callback);	  	        
	  
      d.balance.innerHTML = (dcc)+ ' ' + (r.balance ? fmt_money(r.balance) :'0.00');
    }
    //cost center group/ledger area
    else{
      $dh(d.balance_area);
      d.main_head.innerHTML = r.cost_center_name;
      d.sub_head.dt = 'Cost Center'; d.sub_head.dn = r.name

      d.sub_head1.innerHTML = '' ;
      d.sub_head2.innerHTML = 'Group: ' + parent_account;
      if(r.group_or_ledger=='Ledger') {
        $ds(pscript.ledger_area);
        $dh(pscript.gl_rep);
        $ds(pscript.cc_rep);
        $dh(pscript.group_area);
      } else {
        $dh(pscript.ledger_area);
        $ds(pscript.group_area);
        $ds(pscript.cc_add_btn);
        $dh(pscript.acc_add_btn);
      }

      d.balance.innerHTML ='';
    }
  } else {
    $dh(d.sub_head);
    $dh(pscript.ledger_area);
    $dh(pscript.group_area);
    $dh(d.balance_area);
    d.sub_head1.innerHTML = '';
    d.sub_head2.innerHTML = 'Explore tree on your left to see details';
  }
  
  pscript.acc_period_bal.innerHTML = '';
}

// Group Area
// ----------

pscript.make_group_area = function(type) {
  pscript.group_area = $a(pscript.la,'div','ac_ledger');

  // refresh
   ref_btn = $a(pscript.group_area, 'div', '', {fontSize: '14px',marginBottom: '8px', marginTop: '24px', fontWeight: 'bold'});
  ref_btn.innerHTML = '<img src="images/icons/page_refresh.gif" style="margin-right: 8px"><span class="link_type">Refresh Tree</span>';
  ref_btn.onclick= function() {
    pscript.cur_node.clear_child_nodes();
    pscript.cur_node.expand();
  }
  pscript.group_area.ref_btn = ref_btn;

  // button for acc adding
  pscript.acc_add_btn = $btn(pscript.group_area, '+ Add a child Account', function(){ pscript.new_acc_dialog.show(); });

  // button for cost center adding
  pscript.cc_add_btn = $btn(pscript.group_area, '+ Add a child Cost Center', null);

  //showing new cost center dialog
  pscript.cc_add_btn.onclick = function(){

    // check for cost center name & group or ledger
    pscript.cc_dialog.widgets['Create'].onclick = function() {
      if(!pscript.cc_dialog.widgets['New Cost Center Name'].value) {
        msgprint('Please enter New Cost Center Name'); return;
      }
      if(!sel_val(pscript.cc_dialog.widgets['Group or Ledger'])) {
        msgprint('Please specify cost center is group or ledger'); return;
      }
      //args making
      args = {
        'cost_center_name' : pscript.cc_dialog.widgets['New Cost Center Name'].value,
        'parent_cost_center' : pscript.cur_node.rec.name,
        'group_or_ledger' : sel_val(pscript.cc_dialog.widgets['Group or Ledger']),
        'company_name' : sel_val(pscript.ab_company_sel),
        'company_abbr': '',
        'old_parent':''
      }
      
      //create cost center -- server to gl control
      $c_obj('GL Control', 'add_cc', docstring(args), function(r,rt) { 
        pscript.cc_dialog.widgets['New Cost Center Name'].value='';
        pscript.cc_dialog.hide();
        pscript.group_area.ref_btn.onclick(); 
      });
    }
    
    pscript.new_cost_center_dialog.show();
  }




}

// Ledger Area
// ----------

pscript.make_ledger_area = function() {
  pscript.ledger_area = $a(pscript.la,'div','ac_ledger');

  //General ledger report link
  pscript.gl_rep = $a(pscript.ledger_area, 'div','', {fontSize: '14px',marginBottom: '8px', fontWeight: 'bold'});
  pscript.gl_rep.innerHTML = '<img src="images/icons/report.png" style="margin-right: 8px"><span class="link_type">Open Ledger</span>';
  pscript.gl_rep.onclick = function(){ pscript.make_report('gl'); }

  //Budget report link
  /*pscript.cc_rep = $a(pscript.ledger_area, 'div','', {fontSize: '14px',marginBottom: '8px', fontWeight: 'bold'});
  pscript.cc_rep.innerHTML = '<img src="images/icons/report.png" style="margin-right: 8px"><span class="link_type">Budget vs Actual Analysis Report</span>';
  pscript.cc_rep.onclick = function(){ pscript.make_report('budget'); }*/
}

pscript.make_report = function(flag){
  if(flag=='gl'){
    var callback = function(report){
      report.set_filter('GL Entry', 'Account',pscript.cur_node.rec.name)
      report.dt.run();
    }
    loadreport('GL Entry','General Ledger',callback);
  }
  /*else {
    loadreport('Budget Detail','Periodical Budget Report',function(f){
      f.set_filter('Cost Center','ID',pscript.cur_node.rec.name);
      f.dt.run();
    });
  }*/
}

// New Account
pscript.make_new_acc_dialog = function() {
  var d = new Dialog(300,400,'Create A New Account');
  d.make_body([
    ['HTML','Heading'],
    ['Data','New Account Name'],
    ['Select','Group or Ledger','Specify whether the new account is a Ledger or Group'],
    ['Select','Account Type','[Optional] Specify the type of this account'],
    ['Data','Tax Rate','Specify the default tax rate'],
		['Select','Master Type','Specify the master type of this account'],
    ['Button','Create']
  ]);

  add_sel_options(d.widgets['Group or Ledger'], ['Group', 'Ledger'],'Group');
  add_sel_options(d.widgets['Account Type'], ['', 'Fixed Asset Account','Bank or Cash','Expense Account','Tax','Income Account','Chargeable'], '');
	add_sel_options(d.widgets['Master Type'], ['NA', 'Supplier','Customer','Employee'],'NA');
	
  // hide / show account type
  d.widgets['Group or Ledger'].onchange = function() {
    if(sel_val(this)=='Ledger')$ds(d.rows['Account Type']);
    else $dh(d.rows['Account Type']);
  }

  // hide / show tax rate
  d.widgets['Account Type'].onchange = function() {
    if(sel_val(this)=='Tax' || sel_val(this)=='Chargeable')$ds(d.rows['Tax Rate']);
    else $dh(d.rows['Tax Rate']);
  }

  d.onshow = function() {
    $dh(this.rows['Account Type']);
    $dh(this.rows['Tax Rate']);
    this.widgets['Group or Ledger'].selectedIndex = 0;
    this.widgets['Account Type'].selectedIndex = 0;
		this.widgets['Master Type'].selectedIndex = 0;
    d.widgets['New Account Name'].value = '';
    d.widgets['Tax Rate'].value = '';
  }

  d.widgets['Create'].onclick = function() {
    if(!d.widgets['New Account Name'].value) {
      msgprint('Please enter New Account Name'); return;
    }
		if(!sel_val(d.widgets['Master Type'])) {
      msgprint('Please enter master type of this new account'); return;
    }
    args = {
      'account_name' : d.widgets['New Account Name'].value,
      'parent_account' : pscript.cur_node.rec.name,
      'group_or_ledger' : sel_val(d.widgets['Group or Ledger']),
      'company' : sel_val(pscript.ab_company_sel),
      'account_type' : sel_val(d.widgets['Account Type']),
      'tax_rate' : d.widgets['Tax Rate'].value,
      'master_type': sel_val(d.widgets['Master Type'])
    }
    $c_obj('GL Control', 'add_ac', docstring(args), function(r,rt) { d.hide(); pscript.group_area.ref_btn.onclick(); });
  }
  pscript.new_acc_dialog = d;

}

// New Cost Center
pscript.make_new_cost_center_dialog = function(){
  pscript.cc_dialog = new Dialog(300,400,'Create A New Cost Center');
  pscript.cc_dialog.make_body([
    ['HTML','Heading'],
    ['Data','New Cost Center Name'],
    ['Select','Group or Ledger','Specify whether the new cost center is a Ledger or Group'],
    ['Button','Create']
    ]);

  add_sel_options(pscript.cc_dialog.widgets['Group or Ledger'], ['Group','Ledger'], 'Group');

  pscript.new_cost_center_dialog = pscript.cc_dialog;
}
