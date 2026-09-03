frappe.provide("frappe.treeview_settings");

frappe.treeview_settings["Account"] = {
	breadcrumb: "Accounts",
	title: __("Chart of Accounts"),
	get_tree_root: false,
	filters: [
		{
			fieldname: "company",
			fieldtype: "Select",
			options: erpnext.utils.get_tree_options("company"),
			label: __("Company"),
			render_on_toolbar: true,
			default: erpnext.utils.get_tree_default("company"),
			on_change: function () {
				var me = frappe.treeview_settings["Account"].treeview;
				var company = me.page.fields_dict.company.get_value();
				if (!company) {
					frappe.throw(__("Please set a Company"));
				}
				frappe.call({
					method: "erpnext.accounts.doctype.account.account.get_root_company",
					args: {
						company: company,
					},
					callback: function (r) {
						if (r.message) {
							let root_company = r.message.length ? r.message[0] : "";
							me.page.fields_dict.root_company.set_value(root_company);

							frappe.db.get_value(
								"Company",
								{ name: company },
								"allow_account_creation_against_child_company",
								(r) => {
									frappe.flags.ignore_root_company_validation =
										r.allow_account_creation_against_child_company;
								}
							);
						}
					},
				});
			},
		},
		{
			fieldname: "root_company",
			fieldtype: "Data",
			label: __("Root Company"),
			hidden: true,
			disable_onchange: true,
		},
	],
	root_label: "Accounts",
	get_tree_nodes: "erpnext.accounts.utils.get_children",
	get_label: function (node) {
		// clean display name — the account number renders as a badge (see
		// onrender) instead of being glued into the name
		return frappe.utils.escape_html(node.data.account_name || node.title || node.label);
	},
	onrender: function (node) {
		if (node.is_root || !node.data) return;

		const flags = [];
		if (node.data.account_number) {
			flags.push(frappe.ui.badge({ label: node.data.account_number, theme: "light" }));
		}

		const company = frappe.treeview_settings["Account"].treeview?.page?.fields_dict?.company?.get_value();
		const company_currency = company && erpnext.get_currency(company);
		if (
			node.data.account_currency &&
			company_currency &&
			node.data.account_currency !== company_currency
		) {
			flags.push(frappe.ui.badge({ label: node.data.account_currency, theme: "blue" }));
		}

		if (node.data.freeze_account === "Yes") {
			flags.push(
				frappe.ui.badge({
					label: __("Frozen"),
					icon: "lock",
					title: __("Frozen - entries restricted"),
					theme: "orange",
				})
			);
		}

		erpnext.utils.render_tree_node_flags(node, flags);
	},
	on_node_render: function (node, deep) {
		const render_balances = () => {
			for (let account of cur_tree.account_balance_data) {
				const node = cur_tree.nodes && cur_tree.nodes[account.value];
				if (!node || node.is_root) continue;

				// show Dr if positive since balance is calculated as debit - credit else show Cr
				const balance = account.balance_in_account_currency || account.balance;
				const dr_or_cr = balance > 0 ? __("Dr") : __("Cr");
				const format = (value, currency) => format_currency(Math.abs(value), currency);

				if (account.balance !== undefined) {
					node.parent && node.parent.find(".balance-area").remove();
					$(
						'<span class="balance-area pull-right">' +
							(account.account_currency != account.company_currency
								? format(account.balance_in_account_currency, account.account_currency) +
								  " / "
								: "") +
							format(account.balance, account.company_currency) +
							" " +
							dr_or_cr +
							"</span>"
					).insertBefore(node.$ul);
				}
			}
		};

		if (frappe.boot.user.can_read.indexOf("GL Entry") == -1) return;
		if (!cur_tree.account_balance_data) {
			frappe.db.get_single_value("Accounts Settings", "show_balance_in_coa").then((value) => {
				if (value) {
					frappe.call({
						method: "erpnext.accounts.utils.get_account_balances_coa",
						args: {
							company: cur_tree.args.company,
							include_default_fb_balances: true,
						},
						callback: function (r) {
							if (!r.message || r.message.length === 0) return;
							cur_tree.account_balance_data = r.message || [];
							render_balances();
						},
					});
				}
			});
		} else {
			render_balances();
		}
	},
	add_tree_node: "erpnext.accounts.utils.add_ac",
	menu_items: [
		{
			label: __("New Company"),
			action: function () {
				frappe.new_doc("Company", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Company") !== -1',
		},
	],
	fields: [
		{
			fieldtype: "Data",
			fieldname: "account_name",
			label: __("New Account Name"),
			reqd: true,
			description: __(
				"Name of new Account. Note: Please don't create accounts for Customers and Suppliers"
			),
		},
		{
			fieldtype: "Data",
			fieldname: "account_number",
			label: __("Account Number"),
			description: __("Number of new Account, it will be included in the account name as a prefix"),
		},
		{
			fieldtype: "Check",
			fieldname: "is_group",
			label: __("Is Group"),
			description: __(
				"Further accounts can be made under Groups, but entries can be made against non-Groups"
			),
			onchange: function () {
				if (!this.value) {
					this.layout.set_value("root_type", "");
				}
			},
		},
		{
			fieldtype: "Select",
			fieldname: "root_type",
			label: __("Root Type"),
			options: ["Asset", "Liability", "Equity", "Income", "Expense"].join("\n"),
			depends_on: "eval:doc.is_group && !doc.parent_account",
		},
		{
			fieldtype: "Select",
			fieldname: "account_type",
			label: __("Account Type"),
			options: frappe.get_meta("Account").fields.filter((d) => d.fieldname == "account_type")[0]
				.options,
			description: __("Optional. This setting will be used to filter in various transactions."),
		},
		{
			fieldtype: "Link",
			fieldname: "account_category",
			label: __("Account Category"),
			options: frappe.get_meta("Account").fields.filter((d) => d.fieldname == "account_category")[0]
				.options,
			description: __("Optional. Used with Financial Report Template"),
		},
		{
			fieldtype: "Float",
			fieldname: "tax_rate",
			label: __("Tax Rate"),
			depends_on: 'eval:doc.is_group==0&&doc.account_type=="Tax"',
		},
		{
			fieldtype: "Link",
			fieldname: "account_currency",
			label: __("Currency"),
			options: "Currency",
			description: __("Optional. Sets company's default currency, if not specified."),
		},
	],
	ignore_fields: ["parent_account"],
	onload: function (treeview) {
		frappe.treeview_settings["Account"].treeview = {};
		$.extend(frappe.treeview_settings["Account"].treeview, treeview);
		function get_company() {
			return treeview.page.fields_dict.company.get_value();
		}

		// tools
		treeview.page.add_inner_button(
			__("Chart of Cost Centers"),
			function () {
				frappe.set_route("Tree", "Cost Center", { company: get_company() });
			},
			__("View"),
			"default",
			true
		);

		treeview.page.add_inner_button(
			__("Opening Invoice Creation Tool"),
			function () {
				frappe.set_route("Form", "Opening Invoice Creation Tool", { company: get_company() });
			},
			__("View"),
			"default",
			true
		);

		treeview.page.add_divider_to_button_group(__("View"));

		// financial statements
		for (let report of [
			"Trial Balance",
			"General Ledger",
			"Balance Sheet",
			"Profit and Loss Statement",
			"Cash Flow",
			"Accounts Payable",
			"Accounts Receivable",
		]) {
			treeview.page.add_inner_button(
				__(report),
				function () {
					frappe.set_route("query-report", report, { company: get_company() });
				},
				__("View")
			);
		}
	},
	post_render: function (treeview) {
		frappe.treeview_settings["Account"].treeview["tree"] = treeview.tree;
		if (treeview.can_create) {
			treeview.page.set_primary_action(
				{ label: __("Add Account"), short_label: __("Add") },
				function () {
					let root_company = treeview.page.fields_dict.root_company.get_value();
					if (root_company) {
						frappe.throw(
							__("Please add the account to root level Company - {0}", [root_company])
						);
					} else {
						treeview.new_node();
					}
				},
				"plus"
			);
		}
	},
	toolbar: [
		{
			label: __("Add Child"),
			icon: "plus",
			condition: function (node) {
				return (
					frappe.boot.user.can_create.indexOf("Account") !== -1 &&
					(!frappe.treeview_settings[
						"Account"
					].treeview.page.fields_dict.root_company.get_value() ||
						frappe.flags.ignore_root_company_validation) &&
					node.expandable &&
					!node.hide_add
				);
			},
			click: function () {
				var me = frappe.views.trees["Account"];
				me.new_node();
			},
			btnClass: "hidden-xs",
		},
		{
			condition: function (node) {
				return !node.root && frappe.boot.user.can_read.indexOf("GL Entry") !== -1;
			},
			label: __("View Ledger"),
			icon: "book-open",
			click: function (node, btn) {
				frappe.route_options = {
					from_date: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
					to_date: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
					company:
						frappe.treeview_settings["Account"].treeview.page.fields_dict.company.get_value(),
				};
				if (node.parent_label) {
					frappe.route_options["account"] = node.label;
				}
				frappe.set_route("query-report", "General Ledger");
			},
			btnClass: "hidden-xs",
		},
		{
			// same label and mechanism as the Account form's Actions button:
			// NOT frappe's generic rename (Allow Rename stays off) — this is
			// ERPNext's controlled update that rebuilds the derived
			// "number - name - abbr" document name
			label: __("Update Account Name / Number"),
			icon: "text-cursor-input",
			condition: function (node) {
				return !node.is_root && frappe.model.can_write("Account");
			},
			click: function (node) {
				const dialog = new frappe.ui.Dialog({
					title: __("Update Account Number / Name"),
					fields: [
						{
							fieldtype: "Data",
							fieldname: "account_name",
							label: __("Account Name"),
							reqd: 1,
							default: node.data.account_name,
						},
						{
							fieldtype: "Data",
							fieldname: "account_number",
							label: __("Account Number"),
							default: node.data.account_number,
						},
					],
					primary_action_label: __("Update"),
					primary_action(values) {
						dialog.hide();
						frappe.dom.freeze(__("Updating {0}", [node.label]));
						frappe.call({
							method: "erpnext.accounts.doctype.account.account.update_account_number",
							args: {
								name: node.label,
								account_name: values.account_name,
								account_number: values.account_number,
							},
							callback: function (r) {
								if (r.exc) return;
								const treeview = frappe.views.trees["Account"];
								node.parent_node && treeview.tree.load_children(node.parent_node);
							},
							always: function () {
								frappe.dom.unfreeze();
							},
						});
					},
				});
				dialog.show();
			},
		},
		{
			label: __("Convert to Group"),
			icon: "folder-tree",
			condition: function (node) {
				return !node.is_root && !node.expandable && frappe.model.can_write("Account");
			},
			click: function (node) {
				erpnext.accounts.convert_tree_node("Account", node, "convert_ledger_to_group");
			},
		},
		{
			label: __("Convert to Non-Group"),
			icon: "file-text",
			condition: function (node) {
				// only on groups the user has opened and found empty — a
				// group with children can't convert, so don't offer it
				return (
					!node.is_root &&
					node.expandable &&
					node.loaded &&
					!node.$ul.children().length &&
					frappe.model.can_write("Account")
				);
			},
			click: function (node) {
				erpnext.accounts.convert_tree_node("Account", node, "convert_group_to_ledger");
			},
		},
	],
	extend_toolbar: true,
};

frappe.provide("erpnext.accounts");
// shared by the Account and Cost Center tree views (defined in both files,
// whichever loads first wins): run the doctype's whitelisted convert method,
// then re-render the branch so the node's group/leaf state updates
erpnext.accounts.convert_tree_node =
	erpnext.accounts.convert_tree_node ||
	function (doctype, node, method) {
		frappe.call({
			method: "run_doc_method",
			args: { dt: doctype, dn: node.label, method: method },
			callback: function (r) {
				if (r.exc) return;
				const treeview = frappe.views.trees[doctype];
				node.parent_node && treeview.tree.load_children(node.parent_node);
				frappe.show_alert({ message: __("{0} converted", [node.label]), indicator: "green" });
			},
		});
	};
