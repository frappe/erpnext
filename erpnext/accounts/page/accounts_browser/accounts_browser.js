// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// tree of chart of accounts / cost centers
// multiple companies
// add node
// edit node
// see ledger

pscript['onload_Accounts Browser'] = function(wrapper){
	console.log($(wrapper).html());
	wn.ui.make_app_page({
		parent: wrapper,
		single_column: true
	})
	
	wrapper.appframe.add_module_icon("Accounts");

	var main = $(wrapper).find(".layout-main"),
		chart_area = $("<div>")
			.css({"margin-bottom": "15px", "min-height": "200px"})
			.appendTo(main),
		help_area = $('<div class="well">'+
		'<h4>'+wn._('Quick Help')+'</h4>'+
		'<ol>'+
			'<li>'+wn._('To add child nodes, explore tree and click on the node under which you want to add more nodes.')+'</li>'+
			'<li>'+
			      wn._('Accounting Entries can be made against leaf nodes, called')+
				 '<b>' +wn._('Ledgers')+'</b>.'+ wn._('Entries against') +
				 '<b>' +wn._('Groups') + '</b>'+ wn._('are not allowed.')+
		    '</li>'+
			'<li>'+wn._('Please do NOT create Account (Ledgers) for Customers and Suppliers. They are created directly from the Customer / Supplier masters.')+'</li>'+
			'<li>'+
			     '<b>'+wn._('To create a Bank Account:')+'</b>'+ 
			      wn._('Go to the appropriate group (usually Application of Funds > Current Assets > Bank Accounts)')+
			      wn._('and create a new Account Ledger (by clicking on Add Child) of type "Bank or Cash"')+
			'</li>'+
			'<li>'+
			      '<b>'+wn._('To create a Tax Account:')+'</b>'+
			      wn._('Go to the appropriate group (usually Source of Funds > Current Liabilities > Taxes and Duties)')+
			      wn._('and create a new Account Ledger (by clicking on Add Child) of type "Tax" and do mention the Tax rate.')+
			'</li>'+
		'</ol>'+
		'<p>'+wn._('Please setup your chart of accounts before you start Accounting Entries')+'</p></div>').appendTo(main);
	
	if (wn.boot.profile.can_create.indexOf("Company") !== -1) {
		wrapper.appframe.add_button(wn._('New Company'), function() { newdoc('Company'); },
			'icon-plus');
	}
	
	wrapper.appframe.set_title_right('Refresh', function() {  	
			wrapper.$company_select.change();
		});

	// company-select
	wrapper.$company_select = wrapper.appframe.add_select("Company", [])
		.change(function() {
			var ctype = wn.get_route()[1] || 'Account';
			erpnext.account_chart = new erpnext.AccountsChart(ctype, $(this).val(), 
				chart_area.get(0));
			pscript.set_title(wrapper, ctype, $(this).val());
		})
		
	// load up companies
	return wn.call({
		method:'accounts.page.accounts_browser.accounts_browser.get_companies',
		callback: function(r) {
			wrapper.$company_select.empty();
			$.each(r.message, function(i, v) {
				$('<option>').html(v).attr('value', v).appendTo(wrapper.$company_select);
			});
			wrapper.$company_select.val(wn.defaults.get_default("company") || r[0]).change();
		}
	});
}

pscript.set_title = function(wrapper, ctype, val) {
	if(val) {
		wrapper.appframe.set_title('Chart of '+ctype+'s' + " - " + cstr(val));
	} else {
		wrapper.appframe.set_title('Chart of '+ctype+'s');
	}
}

pscript['onshow_Accounts Browser'] = function(wrapper){
	// set route
	var ctype = wn.get_route()[1] || 'Account';

	if(erpnext.account_chart && erpnext.account_chart.ctype != ctype) {
		wrapper.$company_select.change();
	}
	
	pscript.set_title(wrapper, ctype);
}

erpnext.AccountsChart = Class.extend({
	init: function(ctype, company, wrapper) {
		$(wrapper).empty();
		var me = this;
		me.ctype = ctype;
		me.can_create = wn.model.can_create(this.ctype);
		me.can_delete = wn.model.can_delete(this.ctype);
		me.can_write = wn.model.can_write(this.ctype);
		
		
		me.company = company;
		this.tree = new wn.ui.Tree({
			parent: $(wrapper), 
			label: ctype==="Account" ? "Accounts" : "Cost Centers",
			args: {ctype: ctype, comp: company},
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
				
				// bold
				$('.balance-bold').removeClass('balance-bold'); // deselect
				$(link).parent().find('.balance-area:first').addClass('balance-bold'); // select

			},
			onrender: function(treenode) {
				if (ctype == 'Account' && treenode.data) {
					if(treenode.data.balance) {
						treenode.parent.append('<span class="balance-area">' 
							+ format_currency(treenode.data.balance, treenode.data.currency) 
							+ '</span>');
					}
				}
			}
		});
		this.tree.rootnode.$a.click();
	},
	make_link_toolbar: function(link) {
		var data = $(link).data('node-data');
		if(!data) return;

		link.toolbar = $('<span class="tree-node-toolbar"></span>').insertAfter(link);
		
		var node_links = [];
		// edit
		if (wn.model.can_read(this.ctype) !== -1) {
			node_links.push('<a onclick="erpnext.account_chart.open();">'+wn._('Edit')+'</a>');
		}
		if (data.expandable && wn.boot.profile.in_create.indexOf(this.ctype) !== -1) {
			node_links.push('<a onclick="erpnext.account_chart.new_node();">'+wn._('Add Child')+'</a>');
		} else if (this.ctype === 'Account' && wn.boot.profile.can_read.indexOf("GL Entry") !== -1) {
			node_links.push('<a onclick="erpnext.account_chart.show_ledger();">'+wn._('View Ledger')+'</a>');
		}

		if (this.can_write) {
			node_links.push('<a onclick="erpnext.account_chart.rename()">'+wn._('Rename')+'</a>');
		};
	
		if (this.can_delete) {
			node_links.push('<a onclick="erpnext.account_chart.delete()">'+wn._('Delete')+'</a>');
		};
		
		link.toolbar.append(node_links.join(" | "));
	},
	open: function() {
		var node = this.selected_node();
		wn.set_route("Form", this.ctype, node.data("label"));
	},
	show_ledger: function() {
		var me = this;
		var node = me.selected_node();
		wn.route_options = {
			"account": node.data('label'),
			"from_date": sys_defaults.year_start_date,
			"to_date": sys_defaults.year_end_date
		};
		wn.set_route("general-ledger");
	},
	rename: function() {
		var node = this.selected_node();
		wn.model.rename_doc(this.ctype, node.data('label'), function(new_name) {
			node.parents("ul:first").parent().find(".tree-link:first").trigger("reload");
		});
	},
	delete: function() {
		var node = this.selected_node();
		wn.model.delete_doc(this.ctype, node.data('label'), function() {
			node.parent().remove();
		});
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
			title:wn._('New Account'),
			fields: [
				{fieldtype:'Data', fieldname:'account_name', label:wn._('New Account Name'), reqd:true, 
					description: wn._("Name of new Account. Note: Please don't create accounts for Customers and Suppliers,")+
					wn._("they are created automatically from the Customer and Supplier master")},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:wn._('Group or Ledger'),
					options:'Group\nLedger', description: wn._('Further accounts can be made under Groups,')+
					 	wn._('but entries can be made against Ledger')},
				{fieldtype:'Select', fieldname:'account_type', label:wn._('Account Type'),
					options: ['', 'Fixed Asset Account', 'Bank or Cash', 'Expense Account', 'Tax',
						'Income Account', 'Chargeable'].join('\n'),
					description: wn._("Optional. This setting will be used to filter in various transactions.") },
				{fieldtype:'Float', fieldname:'tax_rate', label:wn._('Tax Rate')},
				{fieldtype:'Button', fieldname:'create_new', label:wn._('Create New') }
			]
		})

		var fd = d.fields_dict;
		
		// account type if ledger
		$(fd.group_or_ledger.input).change(function() {
			if($(this).val()=='Group') {
				$(fd.account_type.wrapper).toggle(false);
				$(fd.tax_rate.wrapper).toggle(false);
			} else {
				$(fd.account_type.wrapper).toggle(true);
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
			v.master_type = '';
			v.company = me.company;
			
			return wn.call({
				args: v,
				method:'accounts.utils.add_ac',
				callback: function(r) {
					$(btn).done_working();
					d.hide();
					node.trigger('reload');
				}
			});
		});
		
		// show
		d.onshow = function() {
			$(fd.group_or_ledger.input).change();
			$(fd.account_type.input).change();
		}
		
		$(fd.group_or_ledger.input).val("Ledger").change();
		d.show();
	},
	
	new_cost_center: function(){
		var me = this;
		// the dialog
		var d = new wn.ui.Dialog({
			title:wn._('New Cost Center'),
			fields: [
				{fieldtype:'Data', fieldname:'cost_center_name', label:wn._('New Cost Center Name'), reqd:true},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:wn._('Group or Ledger'),
					options:'Group\nLedger', description:wn._('Further accounts can be made under Groups,')+
					 	wn._('but entries can be made against Ledger')},
				{fieldtype:'Button', fieldname:'create_new', label:wn._('Create New') }
			]
		});
	
		// create
		$(d.fields_dict.create_new.input).click(function() {
			var btn = this;
			$(btn).set_working();
			var v = d.get_values();
			if(!v) return;
			
			var node = me.selected_node();
			
			v.parent_cost_center = node.data('label');
			v.company = me.company;
			
			return wn.call({
				args: v,
				method:'accounts.utils.add_cc',
				callback: function(r) {
					$(btn).done_working();
					d.hide();
					node.trigger('reload');
				}
			});
		});
		d.show();
	}
});