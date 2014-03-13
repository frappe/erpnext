frappe.pages['setup-wizard'].onload = function(wrapper) { 
	if(sys_defaults.company) {
		frappe.set_route("desktop");
		return;
	}
	$(".navbar:first").toggle(false);
	$("body").css({"padding-top":"30px"});
	
	var wizard_settings = {
		page_name: "setup-wizard",
		parent: wrapper,
		on_complete: function(wiz) {
			var values = wiz.get_values();
			wiz.show_working();
			frappe.call({
				method: "erpnext.setup.page.setup_wizard.setup_wizard.setup_account",
				args: values,
				callback: function(r) {
					if(r.exc) {
						var d = msgprint(frappe._("There were errors."));
						d.custom_onhide = function() {
							frappe.set_route(erpnext.wiz.page_name, "0");
						}
					} else {
						wiz.show_complete();
						setTimeout(function() {
							if(user==="Administrator") {
								msgprint(frappe._("Login with your new User ID") + ":" + values.email);
								setTimeout(function() {
									frappe.app.logout();
								}, 2000);
							} else {
								window.location = "/desk";
							}
						}, 2000);
					}
				}
			})
		},
		title: frappe._("ERPNext Setup Guide"),
		welcome_html: '<h1 class="text-muted text-center"><i class="icon-magic"></i></h1>\
			<h2 class="text-center">'+frappe._('ERPNext Setup')+'</h2>\
			<p class="text-center">' + 
			frappe._('Welcome to ERPNext. Over the next few minutes we will help you setup your ERPNext account. Try and fill in as much information as you have even if it takes a bit longer. It will save you a lot of time later. Good Luck!') + 
			'</p>',
		working_html: '<h3 class="text-muted text-center"><i class="icon-refresh icon-spin"></i></h3>\
			<h2 class="text-center">'+frappe._('Setting up...')+'</h2>\
			<p class="text-center">' + 
			frappe._('Sit tight while your system is being setup. This may take a few moments.') + 
			'</p>',
		complete_html: '<h1 class="text-muted text-center"><i class="icon-thumbs-up"></i></h1>\
			<h2 class="text-center">'+frappe._('Setup Complete!')+'</h2>\
			<p class="text-center">' + 
			frappe._('Your setup is complete. Refreshing...') + 
			'</p>',
		slides: [
			// User
			{
				title: frappe._("The First User: You"),
				icon: "icon-user",
				fields: [
					{"fieldname": "first_name", "label": frappe._("First Name"), "fieldtype": "Data", 
						reqd:1},
					{"fieldname": "last_name", "label": frappe._("Last Name"), "fieldtype": "Data", 
						reqd:1},
					{"fieldname": "email", "label": frappe._("Email Id"), "fieldtype": "Data", 
						reqd:1, "description":"Your Login Id", "options":"Email"},
					{"fieldname": "password", "label": frappe._("Password"), "fieldtype": "Password", 
						reqd:1},
					{fieldtype:"Attach Image", fieldname:"attach_user", 
						label:"Attach Your User..."},
				],
				help: frappe._('The first user will become the System Manager (you can change that later).'),
				onload: function(slide) {
					if(user!=="Administrator") {
						slide.form.fields_dict.password.$wrapper.toggle(false);
						slide.form.fields_dict.email.$wrapper.toggle(false);
						slide.form.fields_dict.first_name.set_input(frappe.boot.user.first_name);
						slide.form.fields_dict.last_name.set_input(frappe.boot.user.last_name);
					
						delete slide.form.fields_dict.email;
						delete slide.form.fields_dict.password;
					}
				}
			},
		
			// Organization
			{
				title: frappe._("The Organization"),
				icon: "icon-building",
				fields: [
					{fieldname:'company_name', label: frappe._('Company Name'), fieldtype:'Data', reqd:1,
						placeholder: 'e.g. "My Company LLC"'},
					{fieldname:'company_abbr', label: frappe._('Company Abbreviation'), fieldtype:'Data',
						placeholder:'e.g. "MC"',reqd:1},
					{fieldname:'fy_start_date', label:'Financial Year Start Date', fieldtype:'Date',
						description:'Your financial year begins on', reqd:1},
					{fieldname:'fy_end_date', label:'Financial Year End Date', fieldtype:'Date',
						description:'Your financial year ends on', reqd:1},
					{fieldname:'company_tagline', label: frappe._('What does it do?'), fieldtype:'Data',
						placeholder:'e.g. "Build tools for builders"', reqd:1},
				],
				help: frappe._('The name of your company for which you are setting up this system.'),
				onload: function(slide) {
					slide.get_input("company_name").on("change", function() {
						var parts = slide.get_input("company_name").val().split(" ");
						var abbr = $.map(parts, function(p) { return p ? p.substr(0,1) : null }).join("");
						slide.get_input("company_abbr").val(abbr.toUpperCase());
					}).val(frappe.boot.control_panel.company_name || "").trigger("change");

					slide.get_input("fy_start_date").on("change", function() {
						var year_end_date = 
							frappe.datetime.add_days(frappe.datetime.add_months(slide.get_input("fy_start_date").val(), 12), -1);
						slide.get_input("fy_end_date").val(year_end_date);
					});
				}
			},
		
			// Country
			{
				title: frappe._("Country, Timezone and Currency"),
				icon: "icon-flag",
				fields: [
					{fieldname:'country', label: frappe._('Country'), reqd:1,
						options: "", fieldtype: 'Select'},
					{fieldname:'currency', label: frappe._('Default Currency'), reqd:1,
						options: "", fieldtype: 'Select'},
					{fieldname:'timezone', label: frappe._('Time Zone'), reqd:1,
						options: "", fieldtype: 'Select'},
				],
				help: frappe._('Select your home country and check the timezone and currency.'),
				onload: function(slide, form) {
					frappe.call({
						method:"frappe.country_info.get_country_timezone_info",
						callback: function(data) {
							erpnext.country_info = data.message.country_info;
							erpnext.all_timezones = data.message.all_timezones;
							slide.get_input("country").empty()
								.add_options([""].concat(keys(erpnext.country_info).sort()));
							slide.get_input("currency").empty()
								.add_options(frappe.utils.unique([""].concat($.map(erpnext.country_info, 
									function(opts, country) { return opts.currency; }))).sort());
							slide.get_input("timezone").empty()
								.add_options([""].concat(erpnext.all_timezones));
						}
					})
			
					slide.get_input("country").on("change", function() {
						var country = slide.get_input("country").val();
						var $timezone = slide.get_input("timezone");
						$timezone.empty();
						// add country specific timezones first
						if(country){
							var timezone_list = erpnext.country_info[country].timezones || [];
							$timezone.add_options(timezone_list.sort());
							slide.get_input("currency").val(erpnext.country_info[country].currency);
						}
						// add all timezones at the end, so that user has the option to change it to any timezone
						$timezone.add_options([""].concat(erpnext.all_timezones));
					});
				}
			},
		
			// Logo
			{
				icon: "icon-bookmark",
				title: frappe._("Logo and Letter Heads"),
				help: frappe._('Upload your letter head and logo - you can edit them later.'),
				fields: [
					{fieldtype:"Attach Image", fieldname:"attach_letterhead", label:"Attach Letterhead..."},
					{fieldtype:"Attach Image", fieldname:"attach_logo", label:"Attach Logo..."},
				],
			},
		
			// Taxes
			{
				icon: "icon-money",
				"title": frappe._("Add Taxes"),
				"help": frappe._("List your tax heads (e.g. VAT, Excise) (upto 3) and their standard rates. This will create a standard template, you can edit and add more later."),
				"fields": [],
			},

			// Customers
			{
				icon: "icon-group",
				"title": frappe._("Your Customers"),
				"help": frappe._("List a few of your customers. They could be organizations or individuals."),
				"fields": [],
			},
		
			// Items to Sell
			{
				icon: "icon-barcode",
				"title": frappe._("Your Products or Services"),
				"help": frappe._("List your products or services that you sell to your customers. Make sure to check the Item Group, Unit of Measure and other properties when you start."),
				"fields": [],
			},

			// Suppliers
			{
				icon: "icon-group",
				"title": frappe._("Your Suppliers"),
				"help": frappe._("List a few of your suppliers. They could be organizations or individuals."),
				"fields": [],
			},

			// Items to Buy
			{
				icon: "icon-barcode",
				"title": frappe._("Products or Services You Buy"),
				"help": frappe._("List a few products or services you buy from your suppliers or vendors. If these are same as your products, then do not add them."),
				"fields": [],
			},

		]
	}
	
	// taxes
	for(var i=1; i<4; i++) {
		wizard_settings.slides[4].fields = wizard_settings.slides[4].fields.concat([
			{fieldtype:"Data", fieldname:"tax_"+ i, label:"Tax " + 1, placeholder:"e.g. VAT"},
			{fieldtype:"Column Break"},
			{fieldtype:"Data", fieldname:"tax_rate_i", label:"Rate (%)", placeholder:"e.g. 5"},
			{fieldtype:"Section Break"},
		])
	}
	
	// customers
	for(var i=1; i<6; i++) {
		wizard_settings.slides[5].fields = wizard_settings.slides[5].fields.concat([
			{fieldtype:"Data", fieldname:"customer_" + i, label:"Customer " + i, 
				placeholder:"Customer Name"},
			{fieldtype:"Column Break"},
			{fieldtype:"Data", fieldname:"customer_contact_" + i, 
				label:"Contact", placeholder:"Contact Name"},
			{fieldtype:"Section Break"}
		])
	}
	
	// products
	for(var i=1; i<6; i++) {
		wizard_settings.slides[6].fields = wizard_settings.slides[6].fields.concat([
			{fieldtype:"Data", fieldname:"item_" + i, label:"Item " + i, 
				placeholder:"A Product or Service"},
			{fieldtype:"Column Break"},
			{fieldtype:"Attach", fieldname:"item_img_" + i, label:"Attach Image..."},
			{fieldtype:"Section Break"},
			{fieldtype:"Column Break"},
			{fieldtype:"Select", label:"Group", fieldname:"item_group_" + i, 
				options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
			{fieldtype:"Column Break"},
			{fieldtype:"Select", fieldname:"item_uom_" + i, label:"UOM",
				options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
			{fieldtype:"Section Break"}
		])
	}

	for(var i=1; i<6; i++) {
		wizard_settings.slides[7].fields = wizard_settings.slides[7].fields.concat([
			{fieldtype:"Data", fieldname:"supplier_" + i, label:"Supplier " + i, 
				placeholder:"Supplier Name"},
			{fieldtype:"Column Break"},
			{fieldtype:"Data", fieldname:"supplier_contact_" + i, 
				label:"Contact", placeholder:"Contact Name"},
			{fieldtype:"Section Break"}
		])
	}

	for(var i=1; i<6; i++) {
		wizard_settings.slides[8].fields = wizard_settings.slides[8].fields.concat([
			{fieldtype:"Data", fieldname:"item_buy_" + i, label:"Item " + i, 
				placeholder:"A Product or Service"},
			{fieldtype:"Column Break"},
			{fieldtype:"Section Break"},
			{fieldtype:"Column Break"},
			{fieldtype:"Select", fieldname:"item_buy_group_" + i, label: "Group",
				options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
			{fieldtype:"Column Break"},
			{fieldtype:"Select", fieldname:"item_buy_uom_" + i, label: "UOM", 
				options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
			{fieldtype:"Section Break"},
		])
	}
	
	erpnext.wiz = new frappe.wiz.Wizard(wizard_settings)
}

frappe.pages['setup-wizard'].onshow = function(wrapper) {
	if(frappe.get_route()[1])
		erpnext.wiz.show(frappe.get_route()[1]);
}

frappe.provide("frappe.wiz");

frappe.wiz.Wizard = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.slides = this.slides;
		this.slide_dict = {};
		this.show_welcome();
	},
	get_message: function(html) {
		return $(repl('<div class="panel panel-default">\
			<div class="panel-body" style="padding: 40px;">%(html)s</div>\
		</div>', {html:html}))
	},
	show_welcome: function() {
		if(this.$welcome) 
			return;
		var me = this;
		this.$welcome = this.get_message(this.welcome_html + 
			'<br><p class="text-center"><button class="btn btn-primary">'+frappe._("Start")+'</button></p>')
			.appendTo(this.parent);
		
		this.$welcome.find(".btn").click(function() {
			me.$welcome.toggle(false);
			me.welcomed = true;
			frappe.set_route(me.page_name, "0");
		})
		
		this.current_slide = {"$wrapper": this.$welcome};
	},
	show_working: function() {
		this.hide_current_slide();
		frappe.set_route(this.page_name);
		this.current_slide = {"$wrapper": this.get_message(this.working_html).appendTo(this.parent)};
	},
	show_complete: function() {
		this.hide_current_slide();
		this.current_slide = {"$wrapper": this.get_message(this.complete_html).appendTo(this.parent)};
	},
	show: function(id) {
		if(!this.welcomed) {
			frappe.set_route(this.page_name);
			return;
		}
		id = cint(id);
		if(this.current_slide && this.current_slide.id===id) 
			return;
		if(!this.slide_dict[id]) {
			this.slide_dict[id] = new frappe.wiz.WizardSlide($.extend(this.slides[id], {wiz:this, id:id}));
			this.slide_dict[id].make();
		}
		
		this.hide_current_slide();
		
		this.current_slide = this.slide_dict[id];
		this.current_slide.$wrapper.toggle(true);
	},
	hide_current_slide: function() {
		if(this.current_slide) {
			this.current_slide.$wrapper.toggle(false);
			this.current_slide = null;
		}
	},
	get_values: function() {
		var values = {};
		$.each(this.slide_dict, function(id, slide) {
			$.extend(values, slide.values)
		})
		return values;
	}
});

frappe.wiz.WizardSlide = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
	},
	make: function() {
		var me = this;
		this.$wrapper = $(repl('<div class="panel panel-default">\
			<div class="panel-heading">\
				<div class="panel-title row">\
					<div class="col-sm-8"><h3 style="margin: 0px;">\
						<i class="%(icon)s text-muted"></i> %(title)s</h3></div>\
					<div class="col-sm-4 text-right"><a class="prev-btn hide btn btn-default">Previous</a> \
						<a class="next-btn hide btn btn-primary">Next</a> \
						<a class="complete-btn hide btn btn-primary"><b>Complete Setup</b></a>\
					</div>\
				</div>\
			</div>\
			<div class="panel-body">\
				<div class="progress">\
					<div class="progress-bar" style="width: %(width)s%"></div>\
				</div>\
				<br>\
				<div class="row">\
					<div class="col-sm-8 form"></div>\
					<div class="col-sm-4 help">\
						<p class="text-muted">%(help)s</p>\
					</div>\
				</div>\
				<hr>\
				<div class="footer"></div>\
			</div>\
		</div>', {help:this.help, title:this.title, main_title:this.wiz.title, step: this.id + 1,
				width: (flt(this.id + 1) / (this.wiz.slides.length+1)) * 100, icon:this.icon}))
			.appendTo(this.wiz.parent);
		
		this.body = this.$wrapper.find(".form")[0];
		
		if(this.fields) {
			this.form = new frappe.ui.FieldGroup({
				fields: this.fields,
				body: this.body,
				no_submit_on_enter: true
			});
			this.form.make();
		} else {
			$(this.body).html(this.html)
		}
		
		if(this.id > 0) {
			this.$prev = this.$wrapper.find('.prev-btn').removeClass("hide")
				.click(function() { 
					frappe.set_route(me.wiz.page_name, me.id-1 + ""); 
				})
				.css({"margin-right": "10px"});
			}
		if(this.id+1 < this.wiz.slides.length) {
			this.$next = this.$wrapper.find('.next-btn').removeClass("hide")
				.click(function() { 
					me.values = me.form.get_values();
					if(me.values===null) 
						return;
					frappe.set_route(me.wiz.page_name, me.id+1 + ""); 
				})
		} else {
			this.$complete = this.$wrapper.find('.complete-btn').removeClass("hide")
				.click(function() { 
					me.values = me.form.get_values();
					if(me.values===null) 
						return;
					me.wiz.on_complete(me.wiz); 
				})
		}
		
		if(this.onload) {
			this.onload(this);
		}

	},
	get_input: function(fn) {
		return this.form.get_input(fn);
	}
})