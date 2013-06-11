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
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'));
	wrapper.appframe.add_home_breadcrumb()
	wrapper.appframe.add_module_breadcrumb("Accounts")
	
	if (wn.boot.profile.can_create.indexOf("Company") !== -1) {
		wrapper.appframe.add_button('New Company', function() { newdoc('Company'); },
			'icon-plus');
	}
	
	wrapper.appframe.add_button('Refresh', function() {  	
			wrapper.$company_select.change();
		}, 'icon-refresh');

	// company-select
	wrapper.$company_select = $('<select class="accbrowser-company-select"></select>')
		.change(function() {
			var ctype = wn.get_route()[1] || 'Account';
			erpnext.account_chart = new erpnext.AccountsChart(ctype, $(this).val(), wrapper);
			pscript.set_title(wrapper, ctype, $(this).val());
		})
		.appendTo(wrapper.appframe.$w.find('.appframe-toolbar'));
		
	// load up companies
	wn.call({
		method:'accounts.page.accounts_browser.accounts_browser.get_companies',
		callback: function(r) {
			wrapper.$company_select.empty();
			$.each(r.message, function(i, v) {
				$('<option>').html(v).attr('value', v).appendTo(wrapper.$company_select);
			});
			wrapper.$company_select.val(sys_defaults.company || r[0]).change();
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
		$(wrapper).find('.tree-area').empty();
		var me = this;
		me.ctype = ctype;
		me.can_create = wn.model.can_create(this.ctype);
		me.can_delete = wn.model.can_delete(this.ctype);
		me.can_write = wn.model.can_write(this.ctype);
		
		
		me.company = company;
		this.tree = new wn.ui.Tree({
			parent: $(wrapper).find('.tree-area'), 
			label: company,
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
			node_links.push('<a onclick="erpnext.account_chart.open();">Edit</a>');
		}
		if (data.expandable && wn.boot.profile.in_create.indexOf(this.ctype) !== -1) {
			node_links.push('<a onclick="erpnext.account_chart.new_node();">Add Child</a>');
		} else if (this.ctype === 'Account' && wn.boot.profile.can_read.indexOf("GL Entry") !== -1) {
			node_links.push('<a onclick="erpnext.account_chart.show_ledger();">View Ledger</a>');
		}

		if (this.can_write) {
			node_links.push('<a onclick="erpnext.account_chart.rename()">Rename</a>');
		};
	
		if (this.can_delete) {
			node_links.push('<a onclick="erpnext.account_chart.delete()">Delete</a>');
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
		wn.set_route("general-ledger", "account=" + node.data('label'));
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
			title:'New Account',
			fields: [
				{fieldtype:'Data', fieldname:'account_name', label:'New Account Name', reqd:true, 
					description: "Name of new Account. Note: Please don't create accounts for Customers and Suppliers, \
					they are created automatically from the Customer and Supplier master"},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:'Group or Ledger',
					options:'Group\nLedger', description:'Further accounts can be made under Groups,\
					 	but entries can be made against Ledger'},
				{fieldtype:'Select', fieldname:'account_type', label:'Account Type',
					options: ['', 'Fixed Asset Account', 'Bank or Cash', 'Expense Account', 'Tax',
						'Income Account', 'Chargeable'].join('\n'),
					description: "Optional. This setting will be used to filter in various transactions." },
				{fieldtype:'Float', fieldname:'tax_rate', label:'Tax Rate'},
				{fieldtype:'Button', fieldname:'create_new', label:'Create New' }
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
			
			wn.call({
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
			title:'New Cost Center',
			fields: [
				{fieldtype:'Data', fieldname:'cost_center_name', label:'New Cost Center Name', reqd:true},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:'Group or Ledger',
					options:'Group\nLedger', description:'Further accounts can be made under Groups,\
					 	but entries can be made against Ledger'},
				{fieldtype:'Button', fieldname:'create_new', label:'Create New' }
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
			v.company_name = me.company;
			
			wn.call({
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