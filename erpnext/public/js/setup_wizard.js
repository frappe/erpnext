frappe.provide("erpnext.setup");

frappe.pages["setup-wizard"].on_page_load = function (wrapper) {
	if (frappe.sys_defaults.company) {
		frappe.set_route("desk");
		return;
	}
};

frappe.setup.on("before_load", function () {
	if (
		frappe.boot.setup_wizard_completed_apps?.length &&
		frappe.boot.setup_wizard_completed_apps.includes("erpnext")
	) {
		return;
	}

	erpnext.setup.use_progress_bar();
	erpnext.setup.blur_active_field_before_action();
	erpnext.setup.setup_test_user_autofill();
	erpnext.setup.slides_settings.map(frappe.setup.add_slide);
});

erpnext.setup.use_progress_bar = function () {
	erpnext.setup.ensure_progress_bar_styles();

	if (frappe.setup.SetupWizard.prototype.erpnext_progress_bar_enabled) return;

	const setup_make = frappe.setup.SetupWizard.prototype.make;
	frappe.setup.SetupWizard.prototype.make = function () {
		setup_make.call(this);
		this.$slide_progress.addClass("setup-progress-bar");
		erpnext.setup.update_progress_bar_state(this);
	};

	const setup_refresh = frappe.setup.SetupWizard.prototype.refresh;
	frappe.setup.SetupWizard.prototype.refresh = function (id) {
		setup_refresh.call(this, id);
		erpnext.setup.update_progress_bar_state(this);
	};

	const setup_show_working_state = frappe.setup.SetupWizard.prototype.show_working_state;
	frappe.setup.SetupWizard.prototype.show_working_state = function () {
		setup_show_working_state.call(this);
		this.$slide_progress.addClass("erpnext-progress-hidden");
		this.$abort_btn?.on("click.erpnext_progress_bar", () => {
			this.$slide_progress.removeClass("erpnext-progress-hidden");
		});
	};

	frappe.setup.SetupWizard.prototype.erpnext_progress_bar_enabled = true;
};

erpnext.setup.update_progress_bar_state = function (wizard) {
	if (!wizard?.$slide_progress?.hasClass("setup-progress-bar")) return;

	wizard.$slide_progress.find(".slide-step").each(function () {
		let step_id = cint($(this).attr("data-step-id"));
		$(this).toggleClass("erpnext-step-filled", step_id <= wizard.current_id);
	});
};

erpnext.setup.ensure_progress_bar_styles = function () {
	if ($("#erpnext-setup-progress-bar-styles").length) return;

	$(`<style id="erpnext-setup-progress-bar-styles">
		.setup-progress-bar.slides-progress {
			align-items: center;
			display: flex;
			gap: 0;
			justify-content: center;
			margin-left: auto;
			margin-right: auto;
			max-width: 520px;
			width: min(520px, calc(100vw - 48px));
		}
		.setup-progress-bar.slides-progress .slide-step {
			background-color: var(--control-bg);
			border: 0;
			border-radius: 0;
			flex: 1 1 0;
			height: 6px;
			margin: 0;
			min-width: 0;
			width: auto;
		}
		.setup-progress-bar.slides-progress .slide-step:first-child {
			border-bottom-left-radius: var(--radius-full);
			border-top-left-radius: var(--radius-full);
		}
		.setup-progress-bar.slides-progress .slide-step:last-child {
			border-bottom-right-radius: var(--radius-full);
			border-top-right-radius: var(--radius-full);
		}
		.setup-progress-bar.slides-progress .slide-step.active,
		.setup-progress-bar.slides-progress .slide-step.step-success {
			background-color: var(--control-bg);
			border: 0;
		}
		.setup-progress-bar.slides-progress .slide-step.erpnext-step-filled {
			background-color: var(--ink-gray-9);
			border: 0;
		}
		.setup-progress-bar.slides-progress .slide-step-indicator,
		.setup-progress-bar.slides-progress .slide-step-complete {
			display: none !important;
		}
		.setup-progress-bar.slides-progress.erpnext-progress-hidden {
			display: none;
		}
	</style>`).appendTo("head");
};

erpnext.setup.blur_active_field_before_action = function () {
	if (frappe.setup.SetupWizard.prototype.erpnext_blur_before_action_enabled) return;

	const setup_make = frappe.setup.SetupWizard.prototype.make;
	frappe.setup.SetupWizard.prototype.make = function () {
		setup_make.call(this);
		this.$next_btn.add(this.$complete_btn).on("mousedown touchstart", function () {
			erpnext.setup.blur_active_setup_field();
		});
	};

	const handle_enter_press = frappe.setup.SetupWizard.prototype.handle_enter_press;
	frappe.setup.SetupWizard.prototype.handle_enter_press = function (e) {
		if (e.which === frappe.ui.keyCode.ENTER) {
			erpnext.setup.blur_active_setup_field();
		}
		return handle_enter_press.call(this, e);
	};

	frappe.setup.SetupWizard.prototype.erpnext_blur_before_action_enabled = true;
};

erpnext.setup.blur_active_setup_field = function () {
	let active_element = document.activeElement;
	if (!active_element || !$(active_element).closest(".setup-wizard-slide").length) return;

	$(active_element).trigger("change").blur();
};

erpnext.setup.setup_test_user_autofill = function () {
	let user_slide = frappe.setup.slides_settings?.find((slide) => slide.name === "user");
	if (!user_slide || user_slide.erpnext_test_autofill_setup) return;

	let user_slide_onload = user_slide.onload;
	user_slide.onload = function (slide) {
		user_slide_onload?.call(this, slide);
		erpnext.setup.bind_test_user_autofill(slide);
	};
	user_slide.erpnext_test_autofill_setup = true;
};

erpnext.setup.bind_test_user_autofill = function (slide) {
	let full_name = slide.get_field("full_name");
	let email = slide.get_field("email");
	let password = slide.get_field("password");

	if (!full_name || !email || !password || full_name.erpnext_test_autofill_bound) return;

	full_name.$input.on("input", function () {
		if (full_name.get_value()?.trim().toLowerCase() !== "test") return;

		email.set_value("test@example.com");
		password.set_value("test");
		erpnext.setup.set_test_setup_values();
		slide.reset_action_button_state();
	});

	full_name.erpnext_test_autofill_bound = true;
};

erpnext.setup.set_test_setup_values = function () {
	$.extend(frappe.wizard.values, {
		persona_implementing_for: "My own business",
		persona_company_size: "1–10",
		persona_industry: "Retail",
		persona_current_system: "Nothing yet - starting fresh",
		module_accounting: 1,
		module_stock: 1,
		module_manufacturing: 0,
		module_projects: 0,
		company_name: "Test Company",
		company_abbr: "TC",
		setup_demo: 0,
	});
};

erpnext.setup.slides_settings = [
	{
		// Persona — help us tailor the setup
		name: "persona",
		title: __("A little about you"),
		// subtitle shown under the title
		help: __("A few quick questions so we can set things up the way you work."),
		fields: [
			{
				fieldname: "persona_implementing_for",
				label: __("Who are you setting this up for?"),
				fieldtype: "Select",
				options: ["", "My own business", "A company I work for", "A client I'm consulting for"].join(
					"\n"
				),
				reqd: 1,
			},
			{
				fieldname: "persona_company_size",
				label: __("How big is the team?"),
				fieldtype: "Select",
				options: ["", "1–10", "11–50", "51–200", "201–1,000", "1,000+"].join("\n"),
				reqd: 1,
			},
			{
				fieldname: "persona_industry",
				label: __("What kind of work do you do?"),
				fieldtype: "Select",
				options: [
					"",
					"Manufacturing",
					"Retail",
					"Wholesale / Distribution",
					"E-commerce",
					"Services / Consulting",
					"Construction / Real Estate",
					"Technology / Software",
					"Healthcare",
					"Education",
					"Agriculture",
					"Food & Beverage",
					"Non Profit",
					"Other",
				].join("\n"),
				reqd: 1,
			},
			{
				fieldname: "persona_current_system",
				label: __("What do you use today?"),
				fieldtype: "Select",
				options: [
					"",
					"Tally",
					"QuickBooks",
					"Zoho",
					"Sage",
					"SAP",
					"Microsoft Dynamics",
					"Oracle NetSuite",
					"Xero",
					"Excel / Spreadsheets",
					"Nothing yet - starting fresh",
					"Other",
				].join("\n"),
				reqd: 1,
			},
			{
				fieldtype: "Section Break",
				description: __("Select the modules that you plan to implement"),
			},
			{ fieldname: "module_accounting", label: __("Accounting"), fieldtype: "Check" },
			{ fieldname: "module_stock", label: __("Stock"), fieldtype: "Check" },
			{ fieldtype: "Column Break" },
			{ fieldname: "module_manufacturing", label: __("Manufacturing"), fieldtype: "Check" },
			{ fieldname: "module_projects", label: __("Project Management"), fieldtype: "Check" },
		],

		onload: function (slide) {
			this.bind_industry_modules(slide);
		},

		bind_industry_modules: function (slide) {
			let me = this;
			slide.get_input("persona_industry").on("change", function () {
				me.apply_industry_modules(slide);
			});
		},

		apply_industry_modules: function (slide) {
			let industry = slide.get_field("persona_industry").get_value();
			let modules = erpnext.setup.industry_modules[industry] || ["accounting"];
			["accounting", "stock", "manufacturing", "projects"].forEach(function (module) {
				slide.get_field("module_" + module).set_value(modules.includes(module) ? 1 : 0);
			});
		},
	},
	{
		// Organization
		name: "organization",
		title: __("Setup your organization"),
		fields: [
			{
				fieldname: "company_name",
				label: __("Company Name"),
				fieldtype: "Data",
				reqd: 1,
			},
			{
				fieldname: "company_abbr",
				label: __("Company Abbreviation"),
				fieldtype: "Data",
				reqd: 1,
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "chart_of_accounts",
				label: __("Chart of Accounts"),
				options: "",
				fieldtype: "Select",
			},
			{ fieldname: "view_coa", label: __("View Chart of Accounts"), fieldtype: "Button" },
			{ fieldname: "fy_start_date", label: __("Financial Year Begins On"), fieldtype: "Date", reqd: 1 },
			// end date should be hidden (auto calculated)
			{ fieldname: "fy_end_date", label: __("End Date"), fieldtype: "Date", reqd: 1, hidden: 1 },
			{ fieldtype: "Section Break" },
			{
				fieldname: "setup_demo",
				label: __("Generate Demo Data for Exploration"),
				fieldtype: "Check",
				description: __(
					"If checked, we will create demo data for you to explore the system. This demo data can be erased later."
				),
			},
		],

		onload: function (slide) {
			this.bind_events(slide);
			this.setup_collapsible_chart_of_accounts(slide);
		},

		before_show: function () {
			this.load_chart_of_accounts(this);
			this.set_fy_dates(this);
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

		validate_fy_dates: function () {
			// validate fiscal year start and end dates
			const invalid =
				this.values.fy_start_date == "Invalid date" || this.values.fy_end_date == "Invalid date";
			const start_greater_than_end = this.values.fy_start_date > this.values.fy_end_date;

			if (invalid || start_greater_than_end) {
				frappe.msgprint(__("Please enter valid Financial Year Start and End Dates"));
				return false;
			}

			return true;
		},

		set_fy_dates: function (slide) {
			var country = frappe.wizard.values.country || frappe.defaults.get_default("country");

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
				slide.get_field("fy_start_date").set_value(current_year + "-" + fy[0]);
				slide.get_field("fy_end_date").set_value(next_year + "-" + fy[1]);
			}
		},

		load_chart_of_accounts: function (slide) {
			let country = frappe.wizard.values.country || frappe.defaults.get_default("country");

			if (country) {
				frappe.call({
					method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
					args: { country: country, with_standard: true },
					callback: function (r) {
						if (r.message) {
							slide.get_input("chart_of_accounts").empty().add_options(r.message);
						}
					},
				});
			}
		},

		bind_events: function (slide) {
			let me = this;
			slide.get_input("fy_start_date").on("change", function () {
				var start_date = slide.form.fields_dict.fy_start_date.get_value();
				var year_end_date = frappe.datetime.add_days(frappe.datetime.add_months(start_date, 12), -1);
				slide.form.fields_dict.fy_end_date.set_value(year_end_date);
			});

			slide.get_input("view_coa").on("click", function () {
				let chart_template = slide.form.fields_dict.chart_of_accounts.get_value();
				if (!chart_template) return;

				me.charts_modal(slide, chart_template);
			});

			slide
				.get_input("company_name")
				.on("input", function () {
					let parts = slide.get_input("company_name").val().split(" ");
					let abbr = $.map(parts, function (p) {
						return p ? p.substr(0, 1) : null;
					}).join("");
					slide.get_field("company_abbr").set_value(abbr.slice(0, 10).toUpperCase());
				})
				.val(frappe.boot.sysdefaults.company_name || "")
				.trigger("change");

			slide
				.get_input("company_abbr")
				.on("change", function () {
					let abbr = slide.get_input("company_abbr").val();
					if (abbr.length > 10) {
						frappe.msgprint(__("Company Abbreviation cannot have more than 5 characters"));
						abbr = abbr.slice(0, 10);
					}
					slide.get_field("company_abbr").set_value(abbr);
				})
				.val(frappe.boot.sysdefaults.company_abbr || "")
				.trigger("change");
		},

		setup_collapsible_chart_of_accounts: function (slide) {
			if (slide.organization_advanced_collapsible_setup) return;

			let chart_field = slide.get_field("chart_of_accounts");
			let view_coa_field = slide.get_field("view_coa");
			let fy_start_field = slide.get_field("fy_start_date");
			let $fields = chart_field.$wrapper.add(view_coa_field.$wrapper).add(fy_start_field.$wrapper);
			let $toggle = $(`
				<div class="setup-collapsible-section">
					<button class="setup-collapsible-toggle text-muted" type="button">
						<span>${__("Advanced setup")}</span>
						<span class="setup-collapsible-icon">${frappe.utils.icon("chevron-right", "sm")}</span>
					</button>
				</div>
			`);

			erpnext.setup.ensure_organization_styles();
			chart_field.$wrapper.before($toggle);
			$fields.hide();

			$toggle.on("click", ".setup-collapsible-toggle", function () {
				let expanded = $toggle.hasClass("expanded");
				$toggle.toggleClass("expanded", !expanded);
				$toggle
					.find(".setup-collapsible-icon")
					.html(frappe.utils.icon(expanded ? "chevron-right" : "chevron-down", "sm"));
				$fields.toggle(!expanded);
			});

			slide.organization_advanced_collapsible_setup = true;
		},

		charts_modal: function (slide, chart_template) {
			let parent = __("All Accounts");

			let dialog = new frappe.ui.Dialog({
				title: chart_template,
				fields: [
					{
						fieldname: "expand_all",
						label: __("Expand All"),
						fieldtype: "Button",
						click: function () {
							// expand all nodes on button click
							coa_tree.load_children(coa_tree.root_node, true);
						},
					},
					{
						fieldname: "collapse_all",
						label: __("Collapse All"),
						fieldtype: "Button",
						click: function () {
							// collapse all nodes
							coa_tree
								.get_all_nodes(coa_tree.root_node.data.value, coa_tree.root_node.is_root)
								.then((data_list) => {
									data_list.map((d) => {
										coa_tree.toggle_node(coa_tree.nodes[d.parent]);
									});
								});
						},
					},
				],
			});

			// render tree structure in the dialog modal
			let coa_tree = new frappe.ui.Tree({
				parent: $(dialog.body),
				label: parent,
				expandable: true,
				method: "erpnext.accounts.utils.get_coa",
				args: {
					chart: chart_template,
					parent: parent,
					doctype: "Account",
				},
				onclick: function (node) {
					parent = node.value;
				},
			});

			// add class to show buttons side by side
			const form_container = $(dialog.body).find("form");
			const buttons = $(form_container).find(".frappe-control");
			form_container.addClass("flex");
			buttons.map((index, button) => {
				$(button).css({ "margin-right": "1em" });
			});

			dialog.show();
			coa_tree.load_children(coa_tree.root_node, true); // expand all node trigger
		},
	},
	{
		name: "starter_customers",
		title: __("Add customers"),
		help: __("Enter the details of a few customers"),
		fields: [
			{ fieldname: "starter_customers", fieldtype: "Small Text", hidden: 1 },
			{ fieldname: "starter_customers_html", fieldtype: "HTML" },
		],
		onload: function (slide) {
			this.slide = slide;
			erpnext.setup.render_starter_name_rows(slide, {
				hidden_fieldname: "starter_customers",
				wrapper_fieldname: "starter_customers_html",
				input_name: "customer_name",
				label: __("Customer name"),
				placeholder: __("Acme Retail"),
				opening_placeholder: __("Opening receivable"),
			});
		},
		validate: function () {
			return erpnext.setup.serialize_starter_name_rows(this.slide, "starter_customers", __("Customer"));
		},
	},
	{
		name: "starter_suppliers",
		title: __("Add suppliers"),
		help: __("Enter the details of a few suppliers"),
		fields: [
			{ fieldname: "starter_suppliers", fieldtype: "Small Text", hidden: 1 },
			{ fieldname: "starter_suppliers_html", fieldtype: "HTML" },
		],
		onload: function (slide) {
			this.slide = slide;
			erpnext.setup.render_starter_name_rows(slide, {
				hidden_fieldname: "starter_suppliers",
				wrapper_fieldname: "starter_suppliers_html",
				input_name: "supplier_name",
				label: __("Supplier name"),
				placeholder: __("Sunrise Traders"),
				opening_placeholder: __("Opening payable"),
			});
		},
		validate: function () {
			return erpnext.setup.serialize_starter_name_rows(this.slide, "starter_suppliers", __("Supplier"));
		},
	},
	{
		name: "starter_items",
		title: __("Add items"),
		help: __("Add products or services. Opening stock is optional."),
		fields: [
			{ fieldname: "starter_items", fieldtype: "Small Text", hidden: 1 },
			{ fieldname: "starter_items_html", fieldtype: "HTML" },
		],
		onload: function (slide) {
			this.slide = slide;
			erpnext.setup.render_starter_item_rows(slide);
		},
		validate: function () {
			return erpnext.setup.serialize_starter_item_rows(this.slide);
		},
	},
	{
		name: "starter_bank",
		title: __("Add bank or cash balance"),
		help: __("Optional. Add one opening bank or cash balance."),
		fields: [
			{ fieldname: "starter_bank_balance", fieldtype: "Small Text", hidden: 1 },
			{
				fieldname: "starter_bank_account_name",
				label: __("Account Name"),
				fieldtype: "Data",
				placeholder: __("Main Bank"),
			},
			{
				fieldname: "starter_bank_amount",
				label: __("Opening Balance"),
				fieldtype: "Currency",
			},
		],
		onload: function (slide) {
			this.slide = slide;
		},
		validate: function () {
			return erpnext.setup.serialize_single_starter_row(this.slide, "starter_bank_balance", {
				account_name: "starter_bank_account_name",
				amount: "starter_bank_amount",
			});
		},
	},
	{
		name: "starter_review",
		title: __("Review starter data"),
		help: __("These records will be created when setup finishes."),
		fields: [{ fieldname: "starter_review_html", fieldtype: "HTML" }],
		before_show: function () {
			erpnext.setup.render_starter_review(this);
		},
	},
];

erpnext.setup.render_starter_name_rows = function (slide, options) {
	erpnext.setup.ensure_starter_spacing();
	let wrapper = slide.get_field(options.wrapper_fieldname).$wrapper;
	wrapper.html(`
		<div class="erpnext-starter-rows" data-hidden-fieldname="${options.hidden_fieldname}">
			<div class="starter-row-list"></div>
			<button class="btn btn-sm btn-link starter-add-row" type="button">${__("+ Add another")}</button>
		</div>
	`);

	let add_row = function (value) {
		let show_label = wrapper.find(".starter-row").length === 0;
		let row = $(`
			<div class="starter-row">
				${show_label ? `<label>${options.label}</label>` : ""}
				<div class="starter-row-control flex align-center">
					<input class="form-control starter-name-input" data-key="${options.input_name}" placeholder="${
			options.placeholder || ""
		}">
					<button class="btn btn-sm btn-secondary starter-remove-row" type="button">${__("Remove")}</button>
				</div>
				${
					options.opening_placeholder
						? `<input class="form-control starter-opening-amount" type="text" inputmode="decimal" placeholder="${options.opening_placeholder}">`
						: ""
				}
			</div>
		`);
		row.find(".starter-name-input").val(value || "");
		wrapper.find(".starter-row-list").append(row);
		return row;
	};

	add_row();
	wrapper.on("click", ".starter-add-row", () => {
		add_row().find(".starter-name-input").focus();
	});
	wrapper.on("click", ".starter-remove-row", function () {
		if (wrapper.find(".starter-row").length > 1) {
			$(this).closest(".starter-row").remove();
		} else {
			$(this).closest(".starter-row").find("input").val("");
		}
	});
	wrapper.on("focus", ".starter-opening-amount", function () {
		let amount = flt($(this).attr("data-value") || $(this).val());
		$(this).val(amount ? amount : "");
	});
	wrapper.on("blur", ".starter-opening-amount", function () {
		let amount = flt($(this).val());
		if (!amount) {
			$(this).val("").removeAttr("data-value");
			return;
		}

		$(this).attr("data-value", amount).val(format_currency(amount));
	});
};

erpnext.setup.serialize_starter_name_rows = function (slide, hidden_fieldname, label) {
	let rows = [];
	let seen = {};
	let duplicate = null;

	slide
		.get_field(hidden_fieldname + "_html")
		.$wrapper.find(".starter-name-input")
		.each(function () {
			let value = ($(this).val() || "").trim();
			if (!value) return;

			let key = value.toLowerCase();
			if (seen[key]) {
				duplicate = value;
				return false;
			}

			seen[key] = true;
			let row = {};
			row[$(this).data("key")] = value;
			let opening_amount_input = $(this).closest(".starter-row").find(".starter-opening-amount");
			let opening_amount = flt(opening_amount_input.attr("data-value") || opening_amount_input.val());
			if (opening_amount) {
				row.opening_amount = opening_amount;
			}
			rows.push(row);
		});

	if (duplicate) {
		frappe.msgprint(__("{0} '{1}' is entered more than once.", [label, duplicate]));
		return false;
	}

	erpnext.setup.set_starter_hidden_value(slide, hidden_fieldname, rows);
	return true;
};

erpnext.setup.render_starter_item_rows = function (slide) {
	erpnext.setup.ensure_starter_spacing();
	let wrapper = slide.get_field("starter_items_html").$wrapper;
	let stock_enabled = !!frappe.wizard.values.module_stock;
	wrapper.html(`
		<div class="erpnext-starter-rows starter-item-rows">
			<div class="starter-row-list"></div>
			<button class="btn btn-sm btn-link starter-add-row" type="button">${__("+ Add another")}</button>
		</div>
	`);

	let add_row = function () {
		let show_label = wrapper.find(".starter-item-row").length === 0;
		let row = $(`
			<div class="starter-row starter-item-row">
				${show_label ? `<label>${__("Item name")}</label>` : ""}
				<div class="starter-row-control flex align-center">
					<input class="form-control starter-item-name" placeholder="${__("Cotton T-Shirt")}">
					<button class="btn btn-sm btn-secondary starter-remove-row" type="button">${__("Remove")}</button>
				</div>
				<div class="starter-checks flex flex-wrap">
					<label><input type="checkbox" data-key="is_sales_item" checked> ${__("Sell")}</label>
					<label><input type="checkbox" data-key="is_purchase_item" checked> ${__("Buy")}</label>
					<label class="starter-stock-check"><input type="checkbox" data-key="is_stock_item"> ${__("Stock")}</label>
				</div>
				<div class="starter-opening-stock">
					<input class="form-control starter-opening-qty" type="number" min="0" step="any" placeholder="${__(
						"Opening stock"
					)}">
				</div>
			</div>
		`);
		row.find('[data-key="is_stock_item"]').prop("checked", stock_enabled);
		if (!stock_enabled) {
			row.find(".starter-stock-check").hide();
			row.find(".starter-opening-stock").hide();
		}
		wrapper.find(".starter-row-list").append(row);
		return row;
	};

	add_row();
	wrapper.on("click", ".starter-add-row", () => {
		add_row().find(".starter-item-name").focus();
	});
	wrapper.on("click", ".starter-remove-row", function () {
		if (wrapper.find(".starter-item-row").length > 1) {
			$(this).closest(".starter-item-row").remove();
		} else {
			$(this).closest(".starter-item-row").find(".starter-item-name").val("");
		}
	});
	wrapper.on("change", '[data-key="is_stock_item"]', function () {
		let row = $(this).closest(".starter-item-row");
		let is_stock_item = $(this).prop("checked");
		row.find(".starter-opening-stock").toggle(is_stock_item);
		if (!is_stock_item) {
			row.find(".starter-opening-qty").val("");
		}
	});
};

erpnext.setup.ensure_starter_spacing = function () {
	if ($("#erpnext-starter-setup-styles").length) return;

	$(`<style id="erpnext-starter-setup-styles">
		.erpnext-starter-rows {
			text-align: left;
		}
		.erpnext-starter-rows .starter-row {
			margin-bottom: 24px;
		}
		.erpnext-starter-rows .starter-row-list .starter-row:last-child {
			margin-bottom: 18px;
		}
		.erpnext-starter-rows .starter-row-control {
			gap: 10px;
		}
		.erpnext-starter-rows .starter-row-control .form-control {
			flex: 1 1 auto;
			min-width: 0;
		}
		.erpnext-starter-rows .starter-remove-row {
			flex: 0 0 auto;
			white-space: nowrap;
		}
		.erpnext-starter-rows .starter-add-row {
			margin-top: 2px;
			padding-left: 0;
			padding-right: 0;
		}
		.erpnext-starter-rows .starter-checks {
			gap: 14px;
			margin-top: 10px;
		}
		.erpnext-starter-rows .starter-checks label {
			margin: 0;
		}
		.erpnext-starter-rows .starter-opening-stock,
		.erpnext-starter-rows .starter-opening-amount {
			margin-top: 10px;
			max-width: 180px;
		}
		.erpnext-starter-review {
			margin: 0 auto;
			max-width: 420px;
			text-align: left;
		}
		.erpnext-starter-review .table {
			margin-bottom: 0;
		}
		@media (max-width: 576px) {
			.erpnext-starter-rows .starter-row-control {
				align-items: stretch;
				flex-direction: column;
			}
			.erpnext-starter-rows .starter-remove-row {
				align-self: flex-start;
			}
		}
	</style>`).appendTo("head");
};

erpnext.setup.ensure_organization_styles = function () {
	if ($("#erpnext-organization-setup-styles").length) return;

	$(`<style id="erpnext-organization-setup-styles">
		.setup-collapsible-section {
			margin-bottom: var(--margin-md);
			text-align: left;
		}
		.setup-collapsible-toggle {
			align-items: center;
			background: transparent;
			border: 0;
			cursor: pointer;
			display: inline-flex;
			gap: 8px;
			font-size: var(--text-base);
			font-weight: 500;
			padding: 0;
		}
		.setup-collapsible-toggle:hover {
			color: var(--text-color);
		}
		.setup-collapsible-icon {
			display: inline-block;
		}
	</style>`).appendTo("head");
};

erpnext.setup.serialize_starter_item_rows = function (slide) {
	let rows = [];
	let seen = {};
	let duplicate = null;

	slide
		.get_field("starter_items_html")
		.$wrapper.find(".starter-item-row")
		.each(function () {
			let row = $(this);
			let item_name = (row.find(".starter-item-name").val() || "").trim();
			if (!item_name) return;

			let key = item_name.toLowerCase();
			if (seen[key]) {
				duplicate = item_name;
				return false;
			}

			seen[key] = true;
			rows.push({
				item_name: item_name,
				is_sales_item: row.find('[data-key="is_sales_item"]').prop("checked") ? 1 : 0,
				is_purchase_item: row.find('[data-key="is_purchase_item"]').prop("checked") ? 1 : 0,
				is_stock_item: row.find('[data-key="is_stock_item"]').prop("checked") ? 1 : 0,
				opening_qty: row.find(".starter-opening-qty").val() || 0,
			});
		});

	if (duplicate) {
		frappe.msgprint(__("Item '{0}' is entered more than once.", [duplicate]));
		return false;
	}

	erpnext.setup.set_starter_hidden_value(slide, "starter_items", rows);
	return true;
};

erpnext.setup.serialize_single_starter_row = function (slide, hidden_fieldname, field_map) {
	let row = {};
	let has_value = false;

	Object.keys(field_map).forEach(function (key) {
		let value = slide.get_field(field_map[key]).get_value();
		if (value) {
			has_value = true;
		}
		row[key] = value;
	});

	erpnext.setup.set_starter_hidden_value(slide, hidden_fieldname, has_value ? [row] : []);
	return true;
};

erpnext.setup.set_starter_hidden_value = function (slide, fieldname, rows) {
	let value = JSON.stringify(rows);
	slide.get_field(fieldname).set_value(value);
	slide.values = slide.values || {};
	slide.values[fieldname] = value;
};

erpnext.setup.render_starter_review = function (slide) {
	let values = frappe.wizard.values || {};
	let counts = [
		[__("Customers"), erpnext.setup.count_starter_rows(values.starter_customers)],
		[__("Suppliers"), erpnext.setup.count_starter_rows(values.starter_suppliers)],
		[__("Items"), erpnext.setup.count_starter_rows(values.starter_items)],
		[__("Opening Stock"), erpnext.setup.count_starter_item_stock_rows(values.starter_items)],
		[__("Opening Receivable"), erpnext.setup.count_starter_opening_amount_rows(values.starter_customers)],
		[__("Opening Payable"), erpnext.setup.count_starter_opening_amount_rows(values.starter_suppliers)],
		[__("Bank/Cash Balance"), erpnext.setup.count_starter_rows(values.starter_bank_balance)],
	];
	let rows = counts
		.filter((d) => d[1])
		.map(
			(d) => `
				<tr>
					<td>${d[0]}</td>
					<td class="text-right">${d[1]}</td>
				</tr>
			`
		)
		.join("");

	slide.get_field("starter_review_html").$wrapper.html(`
		<div class="erpnext-starter-review">
			${
				rows
					? `<table class="table table-bordered">
						<thead>
							<tr>
								<th>${__("Record")}</th>
								<th class="text-right">${__("Count")}</th>
							</tr>
						</thead>
						<tbody>${rows}</tbody>
					</table>`
					: `<p>${__("No starter records selected. Setup can still finish.")}</p>`
			}
		</div>
	`);
};

erpnext.setup.count_starter_rows = function (value) {
	try {
		return (JSON.parse(value || "[]") || []).filter((row) =>
			Object.keys(row || {}).some((key) => row[key])
		).length;
	} catch (e) {
		return 0;
	}
};

erpnext.setup.count_starter_item_stock_rows = function (value) {
	try {
		return (JSON.parse(value || "[]") || []).filter((row) => Number(row.opening_qty || 0) > 0).length;
	} catch (e) {
		return 0;
	}
};

erpnext.setup.count_starter_opening_amount_rows = function (value) {
	try {
		return (JSON.parse(value || "[]") || []).filter((row) => Number(row.opening_amount || 0) > 0).length;
	} catch (e) {
		return 0;
	}
};

// Modules pre-selected on the persona slide based on the chosen industry.
// Keys must match the persona_industry option values. Accounting is always on.
erpnext.setup.industry_modules = {
	Manufacturing: ["accounting", "stock", "manufacturing"],
	Retail: ["accounting", "stock"],
	"Wholesale / Distribution": ["accounting", "stock"],
	"E-commerce": ["accounting", "stock"],
	"Services / Consulting": ["accounting", "projects"],
	"Construction / Real Estate": ["accounting", "stock", "projects"],
	"Technology / Software": ["accounting", "projects"],
	Healthcare: ["accounting", "stock"],
	Education: ["accounting", "projects"],
	Agriculture: ["accounting", "stock"],
	"Food & Beverage": ["accounting", "stock", "manufacturing"],
	"Non Profit": ["accounting", "projects"],
	Other: ["accounting"],
};

// Source: https://en.wikipedia.org/wiki/Fiscal_year
// default 1st Jan - 31st Dec

erpnext.setup.fiscal_years = {
	Afghanistan: ["12-21", "12-20"],
	Australia: ["07-01", "06-30"],
	Bangladesh: ["07-01", "06-30"],
	"Costa Rica": ["10-01", "09-30"],
	Egypt: ["07-01", "06-30"],
	Ethiopia: ["07-08", "07-07"],
	"Hong Kong": ["04-01", "03-31"],
	India: ["04-01", "03-31"],
	Iran: ["06-23", "06-22"],
	Kenya: ["07-01", "06-30"],
	Malaysia: ["07-01", "06-30"],
	Myanmar: ["04-01", "03-31"],
	Nepal: ["07-16", "07-15"],
	"New Zealand": ["04-01", "03-31"],
	Pakistan: ["07-01", "06-30"],
	Singapore: ["04-01", "03-31"],
	"South Africa": ["03-01", "02-28"],
	"United Kingdom": ["04-01", "03-31"],
};
