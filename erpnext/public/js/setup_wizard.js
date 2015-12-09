frappe.provide("erpnext.wiz");

frappe.pages['setup-wizard'].on_page_load = function(wrapper) {
	if(sys_defaults.company) {
		frappe.set_route("desk");
		return;
	}
};

function load_erpnext_slides() {
	$.extend(erpnext.wiz, {
		region: {
			title: __("Region"),
			icon: "icon-flag",
			help: __("Select your Country, Time Zone and Currency"),
			fields: [
				{ fieldname: "country", label: __("Country"), reqd:1,
					fieldtype: "Select" },
				{ fieldname: "timezone", label: __("Time Zone"), reqd:1,
					fieldtype: "Select" },
				{ fieldname: "currency", label: __("Currency"), reqd:1,
					fieldtype: "Select" },
			],

			onload: function(slide) {
				frappe.call({
					method:"frappe.geo.country_info.get_country_timezone_info",
					callback: function(data) {
						erpnext.wiz.region.data = data.message;
						erpnext.wiz.region.setup_fields(slide);
						erpnext.wiz.region.bind_events(slide);
					}
				});
			},
			css_class: "single-column",
			setup_fields: function(slide) {
				var data = erpnext.wiz.region.data;

				slide.get_input("country").empty()
					.add_options([""].concat(keys(data.country_info).sort()));

				slide.get_input("currency").empty()
					.add_options(frappe.utils.unique([""].concat($.map(data.country_info,
						function(opts, country) { return opts.currency; }))).sort());

				slide.get_input("timezone").empty()
					.add_options([""].concat(data.all_timezones));

				if (data.default_country) {
					slide.set_input("country", data.default_country);
				}
			},

			bind_events: function(slide) {
				slide.get_input("country").on("change", function() {
					var country = slide.get_input("country").val();
					var $timezone = slide.get_input("timezone");
					var data = erpnext.wiz.region.data;

					$timezone.empty();

					// add country specific timezones first
					if(country) {
						var timezone_list = data.country_info[country].timezones || [];
						$timezone.add_options(timezone_list.sort());
						slide.get_field("currency").set_input(data.country_info[country].currency);
						slide.get_field("currency").$input.trigger("change");
					}

					// add all timezones at the end, so that user has the option to change it to any timezone
					$timezone.add_options([""].concat(data.all_timezones));

					slide.get_field("timezone").set_input($timezone.val());

					// temporarily set date format
					frappe.boot.sysdefaults.date_format = (data.country_info[country].date_format
						|| "dd-mm-yyyy");
				});

				slide.get_input("currency").on("change", function() {
					var currency = slide.get_input("currency").val();
					if (!currency) return;
					frappe.model.with_doc("Currency", currency, function() {
						frappe.provide("locals.:Currency." + currency);
						var currency_doc = frappe.model.get_doc("Currency", currency);
						var number_format = currency_doc.number_format;
						if (number_format==="#.###") {
							number_format = "#.###,##";
						} else if (number_format==="#,###") {
							number_format = "#,###.##"
						}

						frappe.boot.sysdefaults.number_format = number_format;
						locals[":Currency"][currency] = $.extend({}, currency_doc);
					});
				});
			}
		},

		user: {
			title: __("The First User: You"),
			icon: "icon-user",
			fields: [
				{"fieldname": "first_name", "label": __("First Name"), "fieldtype": "Data",
					reqd:1},
				{"fieldname": "last_name", "label": __("Last Name"), "fieldtype": "Data"},
				{"fieldname": "email", "label": __("Email Address"), "fieldtype": "Data",
					reqd:1, "description": __("You will use it to Login"), "options":"Email"},
				{"fieldname": "password", "label": __("Password"), "fieldtype": "Password",
					reqd:1},
				{fieldtype:"Attach Image", fieldname:"attach_user",
					label: __("Attach Your Picture"), is_private: 0},
			],
			help: __('The first user will become the System Manager (you can change this later).'),
			onload: function(slide) {
				if(user!=="Administrator") {
					slide.form.fields_dict.password.$wrapper.toggle(false);
					slide.form.fields_dict.email.$wrapper.toggle(false);
					slide.form.fields_dict.first_name.set_input(frappe.boot.user.first_name);
					slide.form.fields_dict.last_name.set_input(frappe.boot.user.last_name);

					var user_image = frappe.get_cookie("user_image");
					if(user_image) {
						var $attach_user = slide.form.fields_dict.attach_user.$wrapper;
						$attach_user.find(".missing-image").toggle(false);
						$attach_user.find("img").attr("src", decodeURIComponent(user_image)).toggle(true);
					}

					delete slide.form.fields_dict.email;
					delete slide.form.fields_dict.password;
				}
			},
			css_class: "single-column"
		},

		org: {
			title: __("The Organization"),
			icon: "icon-building",
			fields: [
				{fieldname:'company_name', label: __('Company Name'), fieldtype:'Data', reqd:1,
					placeholder: __('e.g. "My Company LLC"')},
				{fieldname:'company_abbr', label: __('Company Abbreviation'), fieldtype:'Data',
					description: __('Max 5 characters'), placeholder: __('e.g. "MC"'), reqd:1},
				{fieldname:'company_tagline', label: __('What does it do?'), fieldtype:'Data',
					placeholder:__('e.g. "Build tools for builders"'), reqd:1},
				{fieldname:'bank_account', label: __('Bank Account'), fieldtype:'Data',
					placeholder: __('e.g. "XYZ National Bank"'), reqd:1 },
				{fieldname:'chart_of_accounts', label: __('Chart of Accounts'),
					options: "", fieldtype: 'Select'},

				// TODO remove this
				{fieldtype: "Section Break"},
				{fieldname:'fy_start_date', label:__('Financial Year Start Date'), fieldtype:'Date',
					description: __('Your financial year begins on'), reqd:1},
				{fieldname:'fy_end_date', label:__('Financial Year End Date'), fieldtype:'Date',
					description: __('Your financial year ends on'), reqd:1},
			],
			help: __('The name of your company for which you are setting up this system.'),

			onload: function(slide) {
				erpnext.wiz.org.load_chart_of_accounts(slide);
				erpnext.wiz.org.bind_events(slide);
				erpnext.wiz.org.set_fy_dates(slide);
			},

			validate: function() {
				// validate fiscal year start and end dates
				if (this.values.fy_start_date=='Invalid date' || this.values.fy_end_date=='Invalid date') {
					msgprint(__("Please enter valid Financial Year Start and End Dates"));
					return false;
				}

				if ((this.values.company_name || "").toLowerCase() == "company") {
					msgprint(__("Company Name cannot be Company"));
					return false;
				}

				return true;
			},

			css_class: "single-column",

			set_fy_dates: function(slide) {
				var country = slide.wiz.get_values().country;

				if(country) {
					var fy = erpnext.wiz.fiscal_years[country];
					var current_year = moment(new Date()).year();
					var next_year = current_year + 1;
					if(!fy) {
						fy = ["01-01", "12-31"];
						next_year = current_year;
					}

					slide.get_field("fy_start_date").set_input(current_year + "-" + fy[0]);
					slide.get_field("fy_end_date").set_input(next_year + "-" + fy[1]);
				}

			},

			load_chart_of_accounts: function(slide) {
				var country = slide.wiz.get_values().country;

				if(country) {
					frappe.call({
						method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
						args: {"country": country},
						callback: function(r) {
							if(r.message) {
								slide.get_input("chart_of_accounts").empty()
									.add_options(r.message);

								if (r.message.length===1) {
									var field = slide.get_field("chart_of_accounts");
									field.set_value(r.message[0]);
									field.df.hidden = 1;
									field.refresh();
								}
							}
						}
					})
				}
			},

			bind_events: function(slide) {
				slide.get_input("company_name").on("change", function() {
					var parts = slide.get_input("company_name").val().split(" ");
					var abbr = $.map(parts, function(p) { return p ? p.substr(0,1) : null }).join("");
					slide.get_field("company_abbr").set_input(abbr.slice(0, 5).toUpperCase());
				}).val(frappe.boot.sysdefaults.company_name || "").trigger("change");

				slide.get_input("company_abbr").on("change", function() {
					if(slide.get_input("company_abbr").val().length > 5) {
						msgprint("Company Abbreviation cannot have more than 5 characters");
						slide.get_field("company_abbr").set_input("");
					}
				});

				// TODO remove this
				slide.get_input("fy_start_date").on("change", function() {
					var year_end_date =
						frappe.datetime.add_days(frappe.datetime.add_months(
							frappe.datetime.user_to_obj(slide.get_input("fy_start_date").val()), 12), -1);
					slide.get_input("fy_end_date").val(frappe.datetime.obj_to_user(year_end_date));

				});
			}
		},

		branding: {
			icon: "icon-bookmark",
			title: __("The Brand"),
			help: __('Upload your letter head and logo. (you can edit them later).'),
			fields: [
				{fieldtype:"Attach Image", fieldname:"attach_letterhead",
					label: __("Attach Letterhead"),
					description: __("Keep it web friendly 900px (w) by 100px (h)"),
					is_private: 0
				},
				{fieldtype: "Column Break"},
				{fieldtype:"Attach Image", fieldname:"attach_logo",
					label:__("Attach Logo"),
					description: __("100px by 100px"),
					is_private: 0
				},
			],

			css_class: "two-column"
		},

		users: {
			icon: "icon-money",
			"title": __("Add Users"),
			"help": __("Add users to your organization, other than yourself"),
			"fields": [],
			before_load: function(slide) {
				slide.fields = [];
				for(var i=1; i<5; i++) {
					slide.fields = slide.fields.concat([
						{fieldtype:"Section Break"},
						{fieldtype:"Data", fieldname:"user_fullname_"+ i,
							label:__("Full Name")},
						{fieldtype:"Data", fieldname:"user_email_" + i,
							label:__("Email ID"), placeholder:__("user@example.com"),
							options: "Email"},
						{fieldtype:"Column Break"},
						{fieldtype: "Check", fieldname: "user_sales_" + i,
							label:__("Sales"), default: 1},
						{fieldtype: "Check", fieldname: "user_purchaser_" + i,
							label:__("Purchaser"), default: 1},
						{fieldtype: "Check", fieldname: "user_accountant_" + i,
							label:__("Accountant"), default: 1},
					]);
				}
			},
			css_class: "two-column"
		},

		taxes: {
			icon: "icon-money",
			"title": __("Add Taxes"),
			"help": __("List your tax heads (e.g. VAT, Customs etc; they should have unique names) and their standard rates. This will create a standard template, which you can edit and add more later."),
			"fields": [],
			before_load: function(slide) {
				slide.fields = [];
				for(var i=1; i<4; i++) {
					slide.fields = slide.fields.concat([
						{fieldtype:"Section Break"},
						{fieldtype:"Data", fieldname:"tax_"+ i, label:__("Tax") + " " + i,
							placeholder:__("e.g. VAT") + " " + i},
						{fieldtype:"Column Break"},
						{fieldtype:"Float", fieldname:"tax_rate_" + i, label:__("Rate (%)"), placeholder:__("e.g. 5")},
					]);
				}
			},
			css_class: "two-column"
		},

		customers: {
			icon: "icon-group",
			"title": __("Your Customers"),
			"help": __("List a few of your customers. They could be organizations or individuals."),
			"fields": [],
			before_load: function(slide) {
				slide.fields = [];
				for(var i=1; i<6; i++) {
					slide.fields = slide.fields.concat([
						{fieldtype:"Section Break"},
						{fieldtype:"Data", fieldname:"customer_" + i, label:__("Customer") + " " + i,
							placeholder:__("Customer Name")},
						{fieldtype:"Column Break"},
						{fieldtype:"Data", fieldname:"customer_contact_" + i,
							label:__("Contact Name") + " " + i, placeholder:__("Contact Name")}
					])
				}
				slide.fields[1].reqd = 1;
			},
			css_class: "two-column"
		},

		suppliers: {
			icon: "icon-group",
			"title": __("Your Suppliers"),
			"help": __("List a few of your suppliers. They could be organizations or individuals."),
			"fields": [],
			before_load: function(slide) {
				slide.fields = [];
				for(var i=1; i<6; i++) {
					slide.fields = slide.fields.concat([
						{fieldtype:"Section Break"},
						{fieldtype:"Data", fieldname:"supplier_" + i, label:__("Supplier")+" " + i,
							placeholder:__("Supplier Name")},
						{fieldtype:"Column Break"},
						{fieldtype:"Data", fieldname:"supplier_contact_" + i,
							label:__("Contact Name") + " " + i, placeholder:__("Contact Name")},
					])
				}
				slide.fields[1].reqd = 1;
			},
			css_class: "two-column"
		},

		items: {
			icon: "icon-barcode",
			"title": __("Your Products or Services"),
			"help": __("List your products or services that you buy or sell. Make sure to check the Item Group, Unit of Measure and other properties when you start."),
			"fields": [],
			before_load: function(slide) {
				slide.fields = [];
				for(var i=1; i<6; i++) {
					slide.fields = slide.fields.concat([
						{fieldtype:"Section Break", show_section_border: true},
						{fieldtype:"Data", fieldname:"item_" + i, label:__("Item") + " " + i,
							placeholder:__("A Product or Service")},
						{fieldtype:"Select", label:__("Group"), fieldname:"item_group_" + i,
							options:[__("Products"), __("Services"),
								__("Raw Material"), __("Consumable"), __("Sub Assemblies")],
							"default": __("Products")},
						{fieldtype:"Select", fieldname:"item_uom_" + i, label:__("UOM"),
							options:[__("Unit"), __("Nos"), __("Box"), __("Pair"), __("Kg"), __("Set"),
								__("Hour"), __("Minute")],
							"default": __("Unit")},
						{fieldtype: "Check", fieldname: "is_sales_item_" + i, label:__("We sell this Item"), default: 1},
						{fieldtype: "Check", fieldname: "is_purchase_item_" + i, label:__("We buy this Item")},
						{fieldtype:"Column Break"},
						{fieldtype:"Currency", fieldname:"item_price_" + i, label:__("Rate")},
						{fieldtype:"Attach Image", fieldname:"item_img_" + i, label:__("Attach Image"), is_private: 0},
					])
				}
				slide.fields[1].reqd = 1;

				// dummy data
				slide.fields.push({fieldtype: "Section Break"});
				slide.fields.push({fieldtype: "Check", fieldname: "add_sample_data",
					label: __("Add a few sample records"), "default": 1});
			},
			css_class: "two-column"
		},
	});

	// Source: https://en.wikipedia.org/wiki/Fiscal_year
	// default 1st Jan - 31st Dec

	erpnext.wiz.fiscal_years = {
		"Afghanistan": ["12-20", "12-21"],
		"Australia": ["07-01", "06-30"],
		"Bangladesh": ["07-01", "06-30"],
		"Canada": ["04-01", "03-31"],
		"Costa Rica": ["10-01", "09-30"],
		"Egypt": ["07-01", "06-30"],
		"Hong Kong": ["04-01", "03-31"],
		"India": ["04-01", "03-31"],
		"Iran": ["06-23", "06-22"],
		"Italy": ["07-01", "06-30"],
		"Myanmar": ["04-01", "03-31"],
		"New Zealand": ["04-01", "03-31"],
		"Pakistan": ["07-01", "06-30"],
		"Singapore": ["04-01", "03-31"],
		"South Africa": ["03-01", "02-28"],
		"Thailand": ["10-01", "09-30"],
		"United Kingdom": ["04-01", "03-31"],
	};
};

frappe.wiz.on("before_load", function() {
	load_erpnext_slides();
	frappe.wiz.add_slide(erpnext.wiz.user);
	frappe.wiz.add_slide(erpnext.wiz.org);
	frappe.wiz.add_slide(erpnext.wiz.branding);
	frappe.wiz.add_slide(erpnext.wiz.users);
	frappe.wiz.add_slide(erpnext.wiz.taxes);
	frappe.wiz.add_slide(erpnext.wiz.customers);
	frappe.wiz.add_slide(erpnext.wiz.suppliers);
	frappe.wiz.add_slide(erpnext.wiz.items);
	frappe.wiz.welcome_page = "#welcome-to-erpnext";
});
