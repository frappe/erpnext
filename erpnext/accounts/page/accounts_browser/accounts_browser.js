// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// tree of chart of accounts / cost centers
// multiple companies
// add node
// edit node
// see ledger

pscript['onload_Accounts Browser'] = function(wrapper){
	frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	})

	wrapper.appframe.add_module_icon("Accounts");

	var main = $(wrapper).find(".layout-main"),
		chart_area = $("<div>")
			.css({"margin-bottom": "15px", "min-height": "200px"})
			.appendTo(main),
		help_area = $('<div class="well">'+
		'<h4>'+__('Quick Help')+'</h4>'+
		'<ol>'+
			'<li>'+__('To add child nodes, explore tree and click on the node under which you want to add more nodes.')+'</li>'+
			'<li>'+
			      __('Accounting Entries can be made against leaf nodes, called')+
				 ' <b>' +__('Ledgers')+'</b>. '+ __('Entries against ') +
				 '<b>' +__('Groups') + '</b> '+ __('are not allowed.')+
		    '</li>'+
			'<li>'+__('Please do NOT create Account (Ledgers) for Customers and Suppliers. They are created directly from the Customer / Supplier masters.')+'</li>'+
			'<li>'+
			     '<b>'+__('To create a Bank Account')+'</b>: '+
			      __('Go to the appropriate group (usually Application of Funds > Current Assets > Bank Accounts and create a new Account Ledger (by clicking on Add Child) of type "Bank"')+
			'</li>'+
			'<li>'+
			      '<b>'+__('To create a Tax Account') +'</b>: '+
			      __('Go to the appropriate group (usually Source of Funds > Current Liabilities > Taxes and Duties and create a new Account Ledger (by clicking on Add Child) of type "Tax" and do mention the Tax rate.')+
			'</li>'+
		'</ol>'+
		'<p>'+__('Please setup your chart of accounts before you start Accounting Entries')+'</p></div>').appendTo(main);

	if (frappe.boot.user.can_create.indexOf("Company") !== -1) {
		wrapper.appframe.add_button(__('New Company'), function() { newdoc('Company'); },
			'icon-plus');
	}

	wrapper.appframe.set_title_right(__('Refresh'), function() {
			wrapper.$company_select.change();
		});

	// company-select
	wrapper.$company_select = wrapper.appframe.add_select("Company", [])
		.change(function() {
			var ctype = frappe.get_route()[1] || 'Account';
			erpnext.account_chart = new erpnext.AccountsChart(ctype, $(this).val(),
				chart_area.get(0));
			pscript.set_title(wrapper, ctype, $(this).val());
		})

	// load up companies
	return frappe.call({
		method: 'erpnext.accounts.page.accounts_browser.accounts_browser.get_companies',
		callback: function(r) {
			wrapper.$company_select.empty();
			$.each(r.message, function(i, v) {
				$('<option>').html(v).attr('value', v).appendTo(wrapper.$company_select);
			});
			wrapper.$company_select.val(frappe.defaults.get_user_default("company") || r.message[0]).change();
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
	var ctype = frappe.get_route()[1] || 'Account';

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
		me.can_create = frappe.model.can_create(this.ctype);
		me.can_delete = frappe.model.can_delete(this.ctype);
		me.can_write = frappe.model.can_write(this.ctype);


		me.company = company;
		this.tree = new frappe.ui.Tree({
			parent: $(wrapper),
			label: ctype==="Account" ? "Accounts" : "Cost Centers",
			args: {ctype: ctype, comp: company},
			method: 'erpnext.accounts.page.accounts_browser.accounts_browser.get_children',
			click: function(link) {
				// bold
				$('.bold').removeClass('bold'); // deselect
				$(link).parent().find('.balance-area:first').addClass('bold'); // select

			},
			toolbar: [
				{ toggle_btn: true },
				{
					label: __("Open"),
					condition: function(node) { return !node.root },
					click: function(node, btn) {
						 frappe.set_route("Form", me.ctype, node.label);
					}
				},
				{
					condition: function(node) { return !node.root && node.expandable; },
					label: __("Add Child"),
					click: function() {
						if(me.ctype=='Account') {
							me.new_account();
						} else {
							me.new_cost_center();
						}
					}
				},
				{
					condition: function(node) {
						return !node.root && me.ctype === 'Account'
							&& frappe.boot.user.can_read.indexOf("GL Entry") !== -1
					},
					label: __("View Ledger"),
					click: function(node, btn) {
						frappe.route_options = {
							"account": node.label,
							"from_date": sys_defaults.year_start_date,
							"to_date": sys_defaults.year_end_date,
							"company": me.company
						};
						frappe.set_route("query-report", "General Ledger");
					}

				},
				{
					condition: function(node) { return !node.root && me.can_write },
					label: __("Rename"),
					click: function(node) {
						frappe.model.rename_doc(me.ctype, node.label, function(new_name) {
							node.reload();
						});
					}
				},
				{
					condition: function(node) { return !node.root && me.can_delete },
					label: __("Delete"),
					click: function(node) {
						frappe.model.delete_doc(me.ctype, node.label, function() {
							node.parent.remove();
						});
					}
				}
			],
			onrender: function(node) {
				if (me.ctype == 'Account' && node.data && node.data.balance!==undefined) {
					$('<span class="balance-area pull-right text-muted">'
						+ format_currency(node.data.balance, node.data.currency)
						+ '</span>').insertBefore(node.$ul);
				}
			}
		});
	},
	new_account: function() {
		var me = this;

		// the dialog
		var d = new frappe.ui.Dialog({
			title:__('New Account'),
			fields: [
				{fieldtype:'Data', fieldname:'account_name', label:__('New Account Name'), reqd:true,
					description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers, they are created automatically from the Customer and Supplier master")},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:__('Group or Ledger'),
					options:'Group\nLedger', description: __('Further accounts can be made under Groups, but entries can be made against Ledger')},
				{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
					options: ['', 'Bank', 'Cash', 'Warehouse', 'Receivable', 'Payable',
						'Equity', 'Cost of Goods Sold', 'Fixed Asset', 'Expense Account',
						'Income Account', 'Tax', 'Chargeable'].join('\n'),
					description: __("Optional. This setting will be used to filter in various transactions.") },
				{fieldtype:'Float', fieldname:'tax_rate', label:__('Tax Rate')},
				{fieldtype:'Button', fieldname:'create_new', label:__('Create New') }
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
			var v = d.get_values();
			if(!v) return;

			var node = me.tree.get_selected_node();
			v.parent_account = node.label;
			v.master_type = '';
			v.company = me.company;

			return frappe.call({
				args: v,
				method: 'erpnext.accounts.utils.add_ac',
				callback: function(r) {
					d.hide();
					if(node.expanded) {
						node.toggle_node();
					}
					node.reload();
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
		var d = new frappe.ui.Dialog({
			title:__('New Cost Center'),
			fields: [
				{fieldtype:'Data', fieldname:'cost_center_name', label:__('New Cost Center Name'), reqd:true},
				{fieldtype:'Select', fieldname:'group_or_ledger', label:__('Group or Ledger'),
					options:'Group\nLedger', description:__('Further accounts can be made under Groups but entries can be made against Ledger')},
				{fieldtype:'Button', fieldname:'create_new', label:__('Create New') }
			]
		});

		// create
		$(d.fields_dict.create_new.input).click(function() {
			var v = d.get_values();
			if(!v) return;

			var node = me.tree.get_selected_node();

			v.parent_cost_center = node.label;
			v.company = me.company;

			return frappe.call({
				args: v,
				method: 'erpnext.accounts.utils.add_cc',
				callback: function(r) {
					d.hide();
					if(node.expanded) {
						node.toggle_node();
					}
					node.reload();
				}
			});
		});
		d.show();
	}
});
