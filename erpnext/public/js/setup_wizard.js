frappe.provide("erpnext.setup");

frappe.pages['setup-wizard'].on_page_load = function(wrapper) {
	if(frappe.sys_defaults.company) {
		frappe.set_route("desk");
		return;
	}
};

frappe.setup.on("before_load", function () {
	erpnext.setup.slides_settings.map(frappe.setup.add_slide);
});

erpnext.setup.slides_settings = [
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
			{ fieldtype: "Column Break" },
			{
				fieldname: 'company_abbr',
				label: __('Company Abbreviation'),
				fieldtype: 'Data',
				reqd: 1
			},
			{ fieldtype: "Section Break" },
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

			slide.get_input("company_name").on("input", function () {
				let parts = slide.get_input("company_name").val().split(" ");
				let abbr = $.map(parts, function (p) { return p ? p.substr(0, 1) : null }).join("");
				slide.get_field("company_abbr").set_value(abbr.slice(0, 10).toUpperCase());
			}).val(frappe.boot.sysdefaults.company_name || "").trigger("change");

			slide.get_input("company_abbr").on("change", function () {
				let abbr = slide.get_input("company_abbr").val();
				if (abbr.length > 10) {
					frappe.msgprint(__("Company Abbreviation cannot have more than 5 characters"));
					abbr = abbr.slice(0, 10);
				}
				slide.get_field("company_abbr").set_value(abbr);
			}).val(frappe.boot.sysdefaults.company_abbr || "").trigger("change");
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
