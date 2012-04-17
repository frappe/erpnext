// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// tree of chart of accounts / cost centers
// multiple companies
// add node
// edit node
// see ledger

pscript['onload_Accounts Browser'] = function(wrapper){
	wn.require('lib/js/wn/ui/tree.js');
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'));
	wrapper.appframe.add_button('New Company', function() { newdoc('Company'); }, 'icon-plus');
	wrapper.appframe.add_button('Refresh', function() {  
			wrapper.$company_select.change();
		}, 'icon-refresh');

	// company-select
	wrapper.$company_select = $('<select class="accbrowser-company-select"></select>')
		.change(function() {
			var ctype = wn.get_route()[1] || 'Account';
			erpnext.account_chart = new erpnext.AccountsChart(ctype, $(this).val(), wrapper);
		})
		.appendTo(wrapper.appframe.$w.find('.appframe-toolbar'));
		
	// default company
	if(sys_defaults.company) {
		$('<option>')
			.html(sys_defaults.company)
			.attr('value', sys_defaults.company)
			.appendTo(wrapper.$company_select);

		wrapper.$company_select
			.val(sys_defaults.company).change();
	}

	// load up companies
	wn.call({
		method:'accounts.page.accounts_browser.accounts_browser.get_companies',
		callback: function(r) {
			wrapper.$company_select.empty();
			$.each(r.message, function(i, v) {
				$('<option>').html(v).attr('value', v).appendTo(wrapper.$company_select);
			});
			wrapper.$company_select.val(sys_defaults.company || r[0]);
		}
	});
}

pscript['onshow_Accounts Browser'] = function(wrapper){
	// set route
	var ctype = wn.get_route()[1] || 'Account';
	wrapper.appframe.title('Chart of '+ctype+'s');  

	if(erpnext.account_chart && erpnext.account_chart.ctype != ctype) {
		wrapper.$company_select.change();
	} 

}

erpnext.AccountsChart = Class.extend({
	init: function(ctype, company, wrapper) {
		$(wrapper).find('.tree-area').empty();
		var me = this;
		me.ctype = ctype;
		me.company = company;
		this.tree = new wn.ui.Tree({
			parent: $(wrapper).find('.tree-area'), 
			label: company,
			args: {ctype: ctype},
			method: 'accounts.page.accounts_browser.accounts_browser.get_children',
			click: function(link) {
				if(me.cur_toolbar) 
					$(me.cur_toolbar).toggle(false);

				if(!link.toolbar) 
					me.make_link_toolbar(link);

				if(link.toolbar) {
					me.cur_toolbar = link.toolbar;
					$(me.cur_toolbar).toggle(true);					
				}
			
			}
		});
		this.tree.rootnode.$a.click();		
	},
	make_link_toolbar: function(link) {
		var data = $(link).data('node-data');
		if(!data) return;

		link.toolbar = $('<span class="tree-node-toolbar"></span>').insertAfter(link);
		
		// edit
		$('<a href="#!Form/'+encodeURIComponent(this.ctype)+'/'
			+encodeURIComponent(data.value)+'">Edit</a>').appendTo(link.toolbar);

		if(data.expandable) {
			link.toolbar.append(' | <a onclick="erpnext.account_chart.new_node();">Add Child</a>');
		} else if(this.ctype=='Account') {
			link.toolbar.append(' | <a onclick="erpnext.account_chart.show_ledger();">View Ledger</a>');
		}
	},
	show_ledger: function() {
		var me = this;
		var node = me.selected_node();
		wn.set_route('Report', 'GL Entry', 'General Ledger', 
			this.ctype + '=' + node.data('label'));
	},
	new_node: function() {
		if(this.ctype=='Account') {
			this.new_account();
		} else {
			this.new_cost_center();
		}
	},
	selected_node: function() {
		return this.tree.$w.find('.tree-link.selected');
	},
	new_account: function() {
		var me = this;
		
		// the dialog
		var d = new wn.ui.Dialog({
			title:'New Account',
			fields: [
				{fieldtype:'Data', fieldname:'account_name', label:'New Account Name', reqd:true},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:'Group or Ledger',
					options:'Group\nLedger'},
				{fieldtype:'Select', fieldname:'account_type', label:'Account Type',
					options: ['', 'Fixed Asset Account', 'Bank or Cash', 'Expense Account', 'Tax',
						'Income Account', 'Chargeable'].join('\n') },
				{fieldtype:'Float', fieldname:'tax_rate', label:'Tax Rate'},
				{fieldtype:'Select', fieldname:'master_type', label:'Master Type',
					options: ['NA', 'Supplier', 'Customer', 'Employee'].join('\n') },
				{fieldtype:'Button', fieldname:'create_new', label:'Create New' }
			]
		})

		var fd = d.fields_dict;
		
		// account type if ledger
		$(fd.group_or_ledger.input).change(function() {
			if($(this).val()=='Group') {
				$(fd.account_type.wrapper).toggle(false);
				$(fd.master_type.wrapper).toggle(false);
				$(fd.tax_rate.wrapper).toggle(false);
			} else {
				$(fd.account_type.wrapper).toggle(true);
				$(fd.master_type.wrapper).toggle(true);
				if(fd.account_type.get_value()=='Tax') {
					$(fd.tax_rate.wrapper).toggle(true);
				}
			}
		});
		
		// tax rate if tax
		$(fd.account_type.input).change(function() {
			if($(this).val()=='Tax') {
				$(fd.tax_rate.wrapper).toggle(true);				
			} else {
				$(fd.tax_rate.wrapper).toggle(false);				
			}
		})
		
		// create
		$(fd.create_new.input).click(function() {
			var btn = this;
			$(btn).set_working();
			var v = d.get_values();
			if(!v) return;
					
			var node = me.selected_node();
			v.parent_account = node.data('label');
			v.company = me.company;
			
		    $c_obj('GL Control', 'add_ac', v, 
				function(r,rt) { 
					$(btn).done_working();
					d.hide();
					node.trigger('reload'); 	
				});
		});
		
		// show
		d.onshow = function() {
			$(fd.group_or_ledger.input).change();
		}
		d.show();
	},
	
	new_cost_center: function(){
		var me = this;
		// the dialog
		var d = new wn.ui.Dialog({
			title:'New Cost Center',
			fields: [
				{fieldtype:'Data', fieldname:'cost_center_name', label:'New Cost Center Name', reqd:true},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:'Group or Ledger',
					options:'Group\nLedger'},
				{fieldtype:'Button', fieldname:'create_new', label:'Create New' }
			]
		})		
	
		// create
		$(d.fields_dict.create_new.input).click(function() {
			var btn = this;
			$(btn).set_working();
			var v = d.get_values();
			if(!v) return;
			
			var node = me.selected_node();
			
			v.parent_cost_center = node.data('label');
			v.company_name = me.company;
			
		    $c_obj('GL Control', 'add_cc', v, 
				function(r,rt) { 
					$(btn).done_working();
					d.hide();
					node.trigger('reload'); 	
				});
		});
		d.show();
	}
});

/*
pscript.make_chart = function(b, wrapper) {
	pscript.ctype = b;
	$(wrapper).find('.tree-area').empty()
	$(wrapper).find('.layout-sidesection').empty()
  
  //================== table body======================================  
  var ac_main_grid = make_table($i('ab_body'),1,2,'100%',['60%','40%'],{border:"0px", padding:"4px",tableLayout: "fixed", borderCollapse: "collapse"});
  $y($td(ac_main_grid,0,0),{border: "1px solid #dddddd", padding: "8px"});
  pscript.account_tree = $a($td(ac_main_grid,0,0),'div', '',{minHeight:'400px'});
  $y($td(ac_main_grid,0,1),{border: "1px solid #DDD"});
  pscript.la = $a($td(ac_main_grid,0,1),'div');
  pscript.acc_period_bal = $a($td(ac_main_grid,0,1),'div');
  
  //=====================footer area ==================================
  if (pscript.ctype == 'Account') {
    var footer = $a($i('ab_body'),'div','',{backgroundColor: "#FFD", padding: "8px", color: "#444", fontSize: "12px", marginTop: "14px"});
    
    var help1 = $a(footer,'span');
    help1.innerHTML = "<strong>Note:</strong> To create accounts for Customers and Suppliers, please create <a href='#!List/Customer'>Customer</a> and <a href='#!List/Supplier'>Supplier</a>"
      + " Masters. This will ensure that the accounts are linked to your Selling and Buying Processes. The Account Heads for Customer and Supplier will automatically be created."
  }

  // header and toolbar
  // ------------------
  wrapper.appframe.$titlebar.find('.appframe-title').html('Chart of '+pscript.ctype+'s');  

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
  pscript.make_new_cost_center_dialog();

}

pscript.make_ac_tree = function() {
  //var type= sel_val($i('ctype'))
  var type= pscript.ctype;
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
            var imgsrc = 'lib/images/icons/page.png';
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
            var imgsrc = 'lib/images/icons/page.png';
            has_children = false;
          }
          var t = tree.addNode(n, cl[i].cost_center_name, imgsrc,tree.std_onclick, has_children ? tree.std_onexp : null);
          t.rec = cl[i];
          t.parent_account = r.message.parent;
        }
      }
    }

    if (type=='Account'){
      var arg = [node.rec.name, node.rec.account_name, sel_val(pscript.ab_company_sel), pscript.ctype];
    } else{
        var arg = [node.rec.name, node.rec.cost_center_name,sel_val(pscript.ab_company_sel), pscript.ctype];
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
  ref_btn.innerHTML = '<img src="lib/images/icons/page_refresh.gif" style="margin-right: 8px"><span class="link_type">Refresh Tree</span>';
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
  pscript.gl_rep.innerHTML = '<img src="lib/images/icons/report.png" style="margin-right: 8px"><span class="link_type">Open Ledger</span>';
  pscript.gl_rep.onclick = function(){ pscript.make_report('gl'); }

}

pscript.make_report = function(flag){
  if(flag=='gl'){
    var callback = function(report){
      report.set_filter('GL Entry', 'Account',pscript.cur_node.rec.name)
      report.dt.run();
    }
    loadreport('GL Entry','General Ledger',callback);
  }
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
*/