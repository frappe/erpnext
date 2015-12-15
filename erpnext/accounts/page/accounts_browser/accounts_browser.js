// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// tree of chart of accounts / cost centers
// multiple companies
// add node
// edit node
// see ledger

frappe.pages["Accounts Browser"].on_page_load  = function(wrapper){
	frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	})

	frappe.breadcrumbs.add("Accounts");

	var main = wrapper.page.main,
		chart_area = $("<div>")
			.css({"margin-bottom": "15px", "min-height": "200px"})
			.appendTo(main),
		help_area = $('<hr><div style="padding: 0px 15px;">'+
		'<h4>'+__('Quick Help')+'</h4>'+
		'<ol>'+
			'<li>'+__('To add child nodes, explore tree and click on the node under which you want to add more nodes.')+'</li>'+
			'<li>'+
			      __('Accounting Entries can be made against leaf nodes. Entries against Groups are not allowed.')+
		    '</li>'+
			'<li>'+__('Please do NOT create Accounts for Customers and Suppliers. They are created directly from the Customer / Supplier masters.')+'</li>'+
			'<li>'+
			     '<b>'+__('To create a Bank Account')+'</b>: '+
			      __('Go to the appropriate group (usually Application of Funds > Current Assets > Bank Accounts and create a new Account (by clicking on Add Child) of type "Bank"')+
			'</li>'+
			'<li>'+
			      '<b>'+__('To create a Tax Account') +'</b>: '+
			      __('Go to the appropriate group (usually Source of Funds > Current Liabilities > Taxes and Duties and create a new Account (by clicking on Add Child) of type "Tax" and do mention the Tax rate.')+
			'</li>'+
		'</ol>'+
		'<p>'+__('Please setup your chart of accounts before you start Accounting Entries')+'</p></div>').appendTo(main);

	if (frappe.boot.user.can_create.indexOf("Company") !== -1) {
		wrapper.page.add_menu_item(__('New Company'), function() { newdoc('Company'); }, true);
	}

	wrapper.page.add_menu_item(__('Refresh'), function() {
			wrapper.$company_select.change();
		});

	wrapper.page.set_primary_action(__('New'), function() {
		erpnext.account_chart && erpnext.account_chart.make_new();
	}, "octicon octicon-plus");

	// company-select
	wrapper.$company_select = wrapper.page.add_select("Company", [])
		.change(function() {
			var ctype = frappe.get_route()[1] || 'Account';
			erpnext.account_chart = new erpnext.AccountsChart(ctype, $(this).val(),
				chart_area.get(0), wrapper.page);
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

frappe.pages["Accounts Browser"].on_page_show = function(wrapper){
	// set route
	var ctype = frappe.get_route()[1] || 'Account';



	if(erpnext.account_chart && erpnext.account_chart.ctype != ctype) {
		wrapper.$company_select.change();
	}
}

erpnext.AccountsChart = Class.extend({
	init: function(ctype, company, wrapper, page) {
		$(wrapper).empty();
		var me = this;
		me.ctype = ctype;
		me.can_create = frappe.model.can_create(this.ctype);
		me.can_delete = frappe.model.can_delete(this.ctype);
		me.can_write = frappe.model.can_write(this.ctype);
		me.page = page;
		me.set_title();

		// __("Accounts"), __("Cost Centers")

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
					condition: function(node) { return node.expandable; },
					label: __("Add Child"),
					click: function() {
						me.make_new()
					},
					btnClass: "hidden-xs"
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
					},
					btnClass: "hidden-xs"
				},
				{
					condition: function(node) { return !node.root && me.can_write },
					label: __("Rename"),
					click: function(node) {
						frappe.model.rename_doc(me.ctype, node.label, function(new_name) {
							node.reload_parent();
						});
					},
					btnClass: "hidden-xs"
				},
				{
					condition: function(node) { return !node.root && me.can_delete },
					label: __("Delete"),
					click: function(node) {
						frappe.model.delete_doc(me.ctype, node.label, function() {
							node.parent.remove();
						});
					},
					btnClass: "hidden-xs"
				}
			],
			onrender: function(node) {
				var dr_or_cr = node.data.balance < 0 ? "Cr" : "Dr";
				if (me.ctype == 'Account' && node.data && node.data.balance!==undefined) {
					$('<span class="balance-area pull-right text-muted small">'
						+ (node.data.balance_in_account_currency ?
							(format_currency(Math.abs(node.data.balance_in_account_currency),
								node.data.account_currency) + " / ") : "")
						+ format_currency(Math.abs(node.data.balance), node.data.company_currency)
						+ " " + dr_or_cr
						+ '</span>').insertBefore(node.$ul);
				}
			}
		});
	},
	set_title: function(val) {
		var chart_str = this.ctype=="Account" ? __("Chart of Accounts") : __("Chart of Cost Centers");
		if(val) {
			this.page.set_title(chart_str + " - " + cstr(val));
		} else {
			this.page.set_title(chart_str);
		}
	},

	make_new: function() {
		if(this.ctype=='Account') {
			this.new_account();
		} else {
			this.new_cost_center();
		}
	},

	new_account: function() {
		var me = this;

		var node = me.tree.get_selected_node();

		if(!(node && node.expandable)) {
			frappe.msgprint(__("Select a group node first."));
			return;
		}

		// the dialog
		var d = new frappe.ui.Dialog({
			title:__('New Account'),
			fields: [
				{fieldtype:'Data', fieldname:'account_name', label:__('New Account Name'), reqd:true,
					description: __("Name of new Account. Note: Please don't create accounts for Customers and Suppliers")},
				{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
					description: __('Further accounts can be made under Groups, but entries can be made against non-Groups')},
				{fieldtype:'Select', fieldname:'root_type', label:__('Root Type'),
					options: ['Asset', 'Liability', 'Equity', 'Income', 'Expense'].join('\n'),
				},
				{fieldtype:'Select', fieldname:'account_type', label:__('Account Type'),
					options: ['', 'Bank', 'Cash', 'Warehouse', 'Tax', 'Chargeable'].join('\n'),
					description: __("Optional. This setting will be used to filter in various transactions.") },
				{fieldtype:'Float', fieldname:'tax_rate', label:__('Tax Rate')},
				{fieldtype:'Link', fieldname:'warehouse', label:__('Warehouse'), options:"Warehouse"},
				{fieldtype:'Link', fieldname:'account_currency', label:__('Currency'), options:"Currency",
					description: __("Optional. Sets company's default currency, if not specified.")}
			]
		})

		var fd = d.fields_dict;

		// account type if ledger
		$(fd.is_group.input).change(function() {
			if($(this).prop("checked")) {
				$(fd.account_type.wrapper).toggle(false);
				$(fd.tax_rate.wrapper).toggle(false);
				$(fd.warehouse.wrapper).toggle(false);
			} else {
				$(fd.account_type.wrapper).toggle(true);
				fd.account_type.$input.trigger("change");
			}
		});

		// tax rate if tax
		$(fd.account_type.input).change(function() {
			$(fd.tax_rate.wrapper).toggle(fd.account_type.get_value()==='Tax');
			$(fd.warehouse.wrapper).toggle(fd.account_type.get_value()==='Warehouse');
		})

		// root type if root
		$(fd.root_type.wrapper).toggle(node.root);

		// create
		d.set_primary_action(__("Create New"), function() {
			var btn = this;
			var v = d.get_values();
			if(!v) return;

			if(v.account_type==="Warehouse" && !v.warehouse) {
				msgprint(__("Warehouse is required"));
				return;
			}

			var node = me.tree.get_selected_node();
			v.parent_account = node.label;
			v.company = me.company;

			if(node.root) {
				v.is_root = true;
				v.parent_account = null;
			} else {
				v.is_root = false;
				v.root_type = null;
			}

			return frappe.call({
				args: v,
				method: 'erpnext.accounts.utils.add_ac',
				callback: function(r) {
					d.hide();
					if(node.expanded) {
						node.toggle_node();
					}
					node.load();
				}
			});
		});

		// show
		d.on_page_show = function() {
			$(fd.is_group.input).change();
			$(fd.account_type.input).change();
		}

		$(fd.is_group.input).prop("checked", false).change();
		d.show();
	},

	new_cost_center: function(){
		var me = this;
		// the dialog
		var d = new frappe.ui.Dialog({
			title:__('New Cost Center'),
			fields: [
				{fieldtype:'Data', fieldname:'cost_center_name', label:__('New Cost Center Name'), reqd:true},
				{fieldtype:'Check', fieldname:'is_group', label:__('Is Group'),
					description:__('Further cost centers can be made under Groups but entries can be made against non-Groups')},
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
					node.load();
				}
			});
		});
		d.show();
	}
});
