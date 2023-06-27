frappe.provide("erpnext.setup");

frappe.pages['setup-wizard'].on_page_load = function(wrapper) {
	if(frappe.sys_defaults.company) {
		frappe.set_route("desk");
		return;
	}
};
let modal_cards = [];
frappe.setup.on("before_load", function () {
	frappe.require('slides.bundle.css');
	erpnext.setup.slides_settings.map(frappe.setup.add_slide);
});

const set_cards = async () => {
	const get_ws = ({name, hidden}) => {
		return {name: name, type: "Workspace", label_field: "name", hidden}
	};
	// set description in workspace documents.
	// Replace with actual data
	modal_cards["accounting"] = await create_cards(["Accounting", "Buying", "Selling", "Stock"].map((name) => get_ws({name, hidden: ["Selling"].includes(name)})));
	modal_cards["manufacturing"] = await create_cards(["Manufacturing", "Stock", "Accounting", "Buying",].map((name) => get_ws({name, hidden: ["Buying"].includes(name)})));
};

async function before_show() {
	let {name: primary_name, type: primary_type} = frappe.setup.data.primary_domain;
	this.cards.sort((a, b) => primary_name === a.name ? -1 : 1);
	if (this.cards_state.active_cards?.findIndex((a) => a.name == primary_name) == -1) {
		this.cards_state.active_cards.push(frappe.setup.data.primary_domain);
		this.refresh();
		await set_cards();
		default_enabled(primary_type, primary_name);
	} else {
		this.refresh();
	}
	this.onboarding_dialog = new frappe.setup.CardsDialog({
		title: __("Workspace Selector"),
		primary_action_label: __("Save"),
		primary_action: () => {
			this.onboarding_dialog.hide();
			this.refresh();
		},
		
	});
	this.onboarding_dialog.wrapper.classList.add("onboarding-dialog");
	this.slides_footer.find(".next-div > button").filter(function() { return $(this).css("display") != "none" }).on("click", () => {
		const domains = [];
		const workspaces = [];
		this.cards_state.active_cards.forEach((c) => {
				modal_cards[c.name]?.forEach((d) => {
					if (d.enabled) {
						d.domain = c.name;
						!domains.includes(d.domain) && domains.push(d.domain);
						workspaces.push(d);
					}
				})
		});
		frappe.call({
			method: "frappe.core.doctype.domain_settings.domain_settings.set_onboarding_data",
			args: {
				primary_domain: frappe.setup.data.primary_domain.name,
				domains: JSON.stringify(domains),
				workspaces: JSON.stringify(workspaces),
			}
		});
	});
};

const create_cards = async (card_info) => {
	const card_list = [];
	for (let i = 0; i < card_info.length; i++) {
		const { type, name, label_field, hidden = false } = card_info[i];
		let d = await frappe.db.get_doc(type, name);
		card_list.push({
			name: d[label_field],
			description: d.description || "",
			depends_on: d.depends_on?.split("\n")
			.map((c) => c.split(" ")) || [],
			is_hidden: hidden,
			default_enabled: d.default_enabled,
			type: type,
		});
	}
	return card_list;
};

const default_enabled = (card_type, card_name) => {
	const default_enabled = modal_cards[card_name]?.filter((d) => d.default_enabled);
		default_enabled?.forEach((d) => {
			let c = modal_cards[card_name].find((c) => c.name == d.name)
			c.enabled = true;
			c.depends_on?.forEach((dc) => {
				let d = modal_cards[card_name].find((c) => c.type == dc[0] && c.name == dc[1]);
				d.enabled = true;
				if (!d.required_by){
					d.required_by = [[c.type, c.name]];
				} else {
					if (d.required_by.findIndex((r) => r[0] == card_type && r[1] == card_name) == -1){
						d.required_by.push([c.type, c.name])
					}
				}
			});
		});
};

const on_click = (slides, card) => {
	let index = slides.cards_state.active_cards.findIndex((a) => a.name == card.name);
	if (index == -1) {
		slides.cards_state.active_cards.push({ name: card.name, type: card.type || "" });
		default_enabled(card.type, card.name);
		slides.refresh();
	} else {
		slides.onboarding_dialog.set_title(card.label || card.name);
		slides.onboarding_dialog.show();
		slides.onboarding_dialog.cards_selector.card_list = modal_cards[card.name];
		slides.onboarding_dialog.cards_selector.active_parent = card;
		slides.onboarding_dialog.cards_selector.active_parent["slides"] = slides;
		slides.onboarding_dialog.cards_refresh();
	}
}

const on_disable = (card) => {
	card.slides.cards_state.active_cards = card.slides.cards_state.active_cards.filter((c) => c.name != card.name) || [];
	card.slides.refresh();
	card.slides.onboarding_dialog.hide();
}

erpnext.setup.slides_settings = [
	{
		name: 'main_domain',
		title: __("What are you looking for?"),
		desc: __("Choose what describes your business needs the best."),
		icon: "fa fa-building",
		fields: [
			{
				fieldname: 'main_domain',
				label: __('Primary Goal'),
				fieldtype: 'Autocomplete',
				reqd: 1,
				options: [
					{ label: __('Accounting'), value: 'accounting' },
					{ label: __('Manufacturing'), value: 'manufacturing' },
					{ label: __('Inventory / Stock'), value: 'stock_inventory' },
				],
			}
		],
		onload: function (slide) {
			slide.get_input("main_domain").on("change", function () {
				frappe.setup.data.primary_domain = {
					name: slide.form.fields_dict.main_domain.get_value() || "",
					type: "domain",
				};
			});
		},
	},
	{
		name: 'setup_workspace',
		title: __("Setup your Workspace"),
		desc: __("All of the features are enabled in ERPNext.\n This will setup workspaces with the features you need most."),
		before_show,
		cards: [
			{
				name: "accounting",
				label: __('Accounting'),
				description: __("Accounting module solves financial management challenges, streamlining bookkeeping, invoicing, and reporting for improved financial control and informed decision-making."),
				type: "domain",
				features: [
					"Invoicing and Billing",
					"Accounts Payable",
					"Accounts Receivable",
					"General Ledger",
					"Financial Reports",
				],
				button: {
					label: __("Create Workspace"),
					active_label: __("Manage"),
					on_click,
				},
				on_disable
			},
			{
				name: "manufacturing",
				label: __('Manufacturing'),
				description: __("Manufacturing module solves production, inventory, and shop floor challenges, driving operational optimization and cost reduction."),
				type: "domain",
				hue_change: 340,
				features: [
					"Bill of Materials",
					"Production Planning",
					"Shop Floor Management",
					"Quality Control",
					"Costing",
				],
				button: {
					label: __("Create Workspace"),
					active_label: __("Manage"),
					on_click,
				},
				on_disable
			},
			{
				name: "stock_inventory",
				label: __('Stock / Inventory'),
				description: __("Stock / Inventory module optimizes stock tracking, order fulfillment, and demand forecasting, ensuring streamlined supply chain operations and optimized inventory levels."),
				type: "domain",
				hue_change: 320,
				features: [
					"Stock Management",
					"Order Management",
					"Inventory Valuation",
					"Inventory Reports",
					"Item Variants",
				],
				button: {
					label: __("Create Workspace"),
					active_label: __("Disable"),
					on_click,
				},
				on_disable
			},
		],
	},
	{
		// Organization
		name: 'organization',
		title: __("Setup your organization"),
		icon: "fa fa-building",
		fields: [
			{
				fieldname: 'company_name',
				label: __('Company Name'),
				fieldtype: 'Data',
				reqd: 1
			},
			{
				fieldname: 'company_abbr',
				label: __('Company Abbreviation'),
				fieldtype: 'Data',
				hidden: 1
			},
			{
				fieldname: 'chart_of_accounts', label: __('Chart of Accounts'),
				options: "", fieldtype: 'Select'
			},
			{ fieldname: 'view_coa', label: __('View Chart of Accounts'), fieldtype: 'Button' },
			{ fieldname: 'fy_start_date', label: __('Financial Year Begins On'), fieldtype: 'Date', reqd: 1 },
			// end date should be hidden (auto calculated)
			{ fieldname: 'fy_end_date', label: __('End Date'), fieldtype: 'Date', reqd: 1, hidden: 1 },
		],

		onload: function (slide) {
			this.slide = slide;
			this.bind_events(slide);
			this.load_chart_of_accounts(slide);
			this.set_fy_dates(slide);
		},
		validate: function () {
			if (!this.validate_fy_dates()) {
				return false;
			}

			if ((this.values.company_name || "").toLowerCase() == "company") {
				frappe.msgprint(__("Company Name cannot be Company"));
				return false;
			}
			if (!this.values.company_abbr) {
				return false;
			}
			if (this.values.company_abbr.length > 10) {
				return false;
			}

			return true;
		},

		validate_fy_dates: function() {
			// validate fiscal year start and end dates
			const invalid = this.values.fy_start_date == 'Invalid date' ||
				this.values.fy_end_date == 'Invalid date';
			const start_greater_than_end = this.values.fy_start_date > this.values.fy_end_date;

			if (invalid || start_greater_than_end) {
				frappe.msgprint(__("Please enter valid Financial Year Start and End Dates"));
				return false;
			}

			return true;
		},

		set_fy_dates: function (slide) {
			var country = frappe.wizard.values.country;

			if (country) {
				let fy = erpnext.setup.fiscal_years[country];
				let current_year = moment(new Date()).year();
				let next_year = current_year + 1;
				if (!fy) {
					fy = ["01-01", "12-31"];
					next_year = current_year;
				}

				let year_start_date = current_year + "-" + fy[0];
				if (year_start_date > frappe.datetime.get_today()) {
					next_year = current_year;
					current_year -= 1;
				}
				slide.get_field("fy_start_date").set_value(current_year + '-' + fy[0]);
				slide.get_field("fy_end_date").set_value(next_year + '-' + fy[1]);
			}
		},


		load_chart_of_accounts: function (slide) {
			let country = frappe.wizard.values.country;

			if (country) {
				frappe.call({
					method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
					args: { "country": country, with_standard: true },
					callback: function (r) {
						if (r.message) {
							slide.get_input("chart_of_accounts").empty()
								.add_options(r.message);
						}
					}
				})
			}
		},

		bind_events: function (slide) {
			let me = this;
			slide.get_input("fy_start_date").on("change", function () {
				var start_date = slide.form.fields_dict.fy_start_date.get_value();
				var year_end_date =
					frappe.datetime.add_days(frappe.datetime.add_months(start_date, 12), -1);
				slide.form.fields_dict.fy_end_date.set_value(year_end_date);
			});

			slide.get_input("view_coa").on("click", function() {
				let chart_template = slide.form.fields_dict.chart_of_accounts.get_value();
				if(!chart_template) return;

				me.charts_modal(slide, chart_template);
			});

			slide.get_input("company_name").on("change", function () {
				let parts = slide.get_input("company_name").val().split(" ");
				let abbr = $.map(parts, function (p) { return p ? p.substr(0, 1) : null }).join("");
				slide.get_field("company_abbr").set_value(abbr.slice(0, 10).toUpperCase());
			}).val(frappe.boot.sysdefaults.company_name || "").trigger("change");

			slide.get_input("company_abbr").on("change", function () {
				if (slide.get_input("company_abbr").val().length > 10) {
					frappe.msgprint(__("Company Abbreviation cannot have more than 5 characters"));
					slide.get_field("company_abbr").set_value("");
				}
			});
		},

		charts_modal: function(slide, chart_template) {
			let parent = __('All Accounts');

			let dialog = new frappe.ui.Dialog({
				title: chart_template,
				fields: [
					{'fieldname': 'expand_all', 'label': __('Expand All'), 'fieldtype': 'Button',
						click: function() {
							// expand all nodes on button click
							coa_tree.load_children(coa_tree.root_node, true);
						}
					},
					{'fieldname': 'collapse_all', 'label': __('Collapse All'), 'fieldtype': 'Button',
						click: function() {
							// collapse all nodes
							coa_tree.get_all_nodes(coa_tree.root_node.data.value, coa_tree.root_node.is_root)
								.then(data_list => {
									data_list.map(d => { coa_tree.toggle_node(coa_tree.nodes[d.parent]); });
								});
						}
					}
				]
			});

			// render tree structure in the dialog modal
			let coa_tree = new frappe.ui.Tree({
				parent: $(dialog.body),
				label: parent,
				expandable: true,
				method: 'erpnext.accounts.utils.get_coa',
				args: {
					chart: chart_template,
					parent: parent,
					doctype: 'Account'
				},
				onclick: function(node) {
					parent = node.value;
				}
			});

			// add class to show buttons side by side
			const form_container = $(dialog.body).find('form');
			const buttons = $(form_container).find('.frappe-control');
			form_container.addClass('flex');
			buttons.map((index, button) => {
				$(button).css({"margin-right": "1em"});
			})

			dialog.show();
			coa_tree.load_children(coa_tree.root_node, true); // expand all node trigger
		}
	}
];

// Source: https://en.wikipedia.org/wiki/Fiscal_year
// default 1st Jan - 31st Dec

erpnext.setup.fiscal_years = {
	"Afghanistan": ["12-21", "12-20"],
	"Australia": ["07-01", "06-30"],
	"Bangladesh": ["07-01", "06-30"],
	"Canada": ["04-01", "03-31"],
	"Costa Rica": ["10-01", "09-30"],
	"Egypt": ["07-01", "06-30"],
	"Hong Kong": ["04-01", "03-31"],
	"India": ["04-01", "03-31"],
	"Iran": ["06-23", "06-22"],
	"Myanmar": ["04-01", "03-31"],
	"New Zealand": ["04-01", "03-31"],
	"Pakistan": ["07-01", "06-30"],
	"Singapore": ["04-01", "03-31"],
	"South Africa": ["03-01", "02-28"],
	"Thailand": ["10-01", "09-30"],
	"United Kingdom": ["04-01", "03-31"],
};
