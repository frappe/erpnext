wn.pages['setup-wizard'].onload = function(wrapper) { 
	if(sys_defaults.company) {
		wn.set_route("desktop");
		return;
	}
	$(".navbar:first").toggle(false);
	$("body").css({"padding-top":"30px"});
	
	erpnext.wiz = new wn.wiz.Wizard({
		page_name: "setup-wizard",
		parent: wrapper,
		on_complete: function(wiz) {
			var values = wiz.get_values();
			wiz.show_working();
			wn.call({
				method: "setup.page.setup_wizard.setup_wizard.setup_account",
				args: values,
				callback: function(r) {
					if(r.exc) {
						var d = msgprint(wn._("There were errors."));
						d.custom_onhide = function() {
							wn.set_route(erpnext.wiz.page_name, "0");
						}
					} else {
						wiz.show_complete();
						setTimeout(function() {
							if(user==="Administrator") {
								msgprint(wn._("Login with your new User ID") + ":" + values.email);
								setTimeout(function() {
									wn.app.logout();
								}, 2000);
							} else {
								window.location = "app.html";
							}
						}, 2000);
					}
				}
			})
		},
		title: wn._("ERPNext Setup Guide"),
		welcome_html: '<h1 class="text-muted text-center"><i class="icon-magic"></i></h1>\
			<h2 class="text-center">'+wn._('ERPNext Setup')+'</h2>\
			<p class="text-center">' + 
			wn._('Welcome to ERPNext. Over the next few minutes we will help you setup your ERPNext account. Try and fill in as much information as you have even if it takes a bit longer. It will save you a lot of time later. Good Luck!') + 
			'</p>',
		working_html: '<h3 class="text-muted text-center"><i class="icon-refresh icon-spin"></i></h3>\
			<h2 class="text-center">'+wn._('Setting up...')+'</h2>\
			<p class="text-center">' + 
			wn._('Sit tight while your system is being setup. This may take a few moments.') + 
			'</p>',
		complete_html: '<h1 class="text-muted text-center"><i class="icon-thumbs-up"></i></h1>\
			<h2 class="text-center">'+wn._('Setup Complete!')+'</h2>\
			<p class="text-center">' + 
			wn._('Your setup is complete. Refreshing...') + 
			'</p>',
		slides: [
			// User
			{
				title: wn._("The First User: You"),
				icon: "icon-user",
				fields: [
					{"fieldname": "first_name", "label": wn._("First Name"), "fieldtype": "Data", reqd:1},
					{"fieldname": "last_name", "label": wn._("Last Name"), "fieldtype": "Data", reqd:1},
					{"fieldname": "email", "label": wn._("Email Id"), "fieldtype": "Data", reqd:1, "description":"Your Login Id"},
					{"fieldname": "password", "label": wn._("Password"), "fieldtype": "Password", reqd:1},
					{fieldtype:"Attach Image", fieldname:"attach_profile", label:"Attach Your Profile..."},
				],
				help: wn._('The first user will become the System Manager (you can change that later).'),
				onload: function(slide) {
					if(user!=="Administrator") {
						slide.form.fields_dict.password.$wrapper.toggle(false);
						slide.form.fields_dict.email.$wrapper.toggle(false);
						slide.form.fields_dict.first_name.set_input(wn.boot.profile.first_name);
						slide.form.fields_dict.last_name.set_input(wn.boot.profile.last_name);
						
						delete slide.form.fields_dict.email;
						delete slide.form.fields_dict.password;
					}
				}
			},
			
			// Organization
			{
				title: wn._("The Organization"),
				icon: "icon-building",
				fields: [
					{fieldname:'company_name', label: wn._('Company Name'), fieldtype:'Data', reqd:1,
						placeholder: 'e.g. "My Company LLC"'},
					{fieldname:'company_abbr', label: wn._('Company Abbreviation'), fieldtype:'Data',
						placeholder:'e.g. "MC"',reqd:1},
					{fieldname:'fy_start', label:'Financial Year Start Date', fieldtype:'Select',
						description:'Your financial year begins on', reqd:1,
						options: ['', '1st Jan', '1st Apr', '1st Jul', '1st Oct'] },
					{fieldname:'company_tagline', label: wn._('What does it do?'), fieldtype:'Data',
						placeholder:'e.g. "Build tools for builders"', reqd:1},
				],
				help: wn._('The name of your company for which you are setting up this system.'),
				onload: function(slide) {
					slide.get_input("company_name").on("change", function() {
						var parts = slide.get_input("company_name").val().split(" ");
						var abbr = $.map(parts, function(p) { return p ? p.substr(0,1) : null }).join("");
						slide.get_input("company_abbr").val(abbr.toUpperCase());
					}).val(wn.boot.control_panel.company_name || "").trigger("change");
				}
			},
			
			// Country
			{
				title: wn._("Country, Timezone and Currency"),
				icon: "icon-flag",
				fields: [
					{fieldname:'country', label: wn._('Country'), reqd:1,
						options: "", fieldtype: 'Select'},
					{fieldname:'currency', label: wn._('Default Currency'), reqd:1,
						options: "", fieldtype: 'Select'},
					{fieldname:'timezone', label: wn._('Time Zone'), reqd:1,
						options: "", fieldtype: 'Select'},
				],
				help: wn._('Select your home country and check the timezone and currency.'),
				onload: function(slide, form) {
					wn.call({
						method:"webnotes.country_info.get_country_timezone_info",
						callback: function(data) {
							erpnext.country_info = data.message.country_info;
							erpnext.all_timezones = data.message.all_timezones;
							slide.get_input("country").empty()
								.add_options([""].concat(keys(erpnext.country_info).sort()));
							slide.get_input("currency").empty()
								.add_options(wn.utils.unique([""].concat($.map(erpnext.country_info, 
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
				title: wn._("Logo and Letter Heads"),
				help: wn._('Upload your letter head and logo - you can edit them later.'),
				fields: [
					{fieldtype:"Attach Image", fieldname:"attach_letterhead", label:"Attach Letterhead..."},
					{fieldtype:"Attach Image", fieldname:"attach_logo", label:"Attach Logo..."},
				],
			},
			
			// Taxes
			{
				icon: "icon-money",
				"title": wn._("Add Taxes"),
				"help": wn._("List your tax heads (e.g. VAT, Excise) (upto 3) and their standard rates. This will create a standard template, you can edit and add more later."),
				"fields": [
					{fieldtype:"Data", fieldname:"tax_1", label:"Tax 1", placeholder:"e.g. VAT"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"tax_rate_1", label:"Rate (%)", placeholder:"e.g. 5"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"tax_2", label:"Tax 2", placeholder:"e.g. Customs Duty"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"tax_rate_2", label:"Rate (%)", placeholder:"e.g. 5"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"tax_3", label:"Tax 3", placeholder:"e.g. Excise"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"tax_rate_3", label:"Rate (%)", placeholder:"e.g. 5"},
				],
			},

			// Customers
			{
				icon: "icon-group",
				"title": wn._("Your Customers"),
				"help": wn._("List a few of your customers. They could be organizations or individuals."),
				"fields": [
					{fieldtype:"Data", fieldname:"customer_1", label:"Customer 1", placeholder:"Customer Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"customer_contact_1", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"customer_2", label:"Customer 2", placeholder:"Customer Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"customer_contact_2", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"customer_3", label:"Customer 3", placeholder:"Customer Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"customer_contact_3", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"customer_4", label:"Customer 4", placeholder:"Customer Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"customer_contact_4", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"customer_5", label:"Customer 5", placeholder:"Customer Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"customer_contact_5", label:"", placeholder:"Contact Name"},
				],
			},
			
			// Items to Sell
			{
				icon: "icon-barcode",
				"title": wn._("Your Products or Services"),
				"help": wn._("List your products or services that you sell to your customers. Make sure to check the Item Group, Unit of Measure and other properties when you start."),
				"fields": [
					{fieldtype:"Data", fieldname:"item_1", label:"Item 1", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Attach", fieldname:"item_img_1", label:"Attach Image..."},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_group_1", options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_uom_1", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_2", label:"Item 2", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Attach", fieldname:"item_img_2", label:"Attach Image..."},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_group_2", options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_uom_2", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_3", label:"Item 3", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Attach", fieldname:"item_img_3", label:"Attach Image..."},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_group_3", options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_uom_3", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_4", label:"Item 4", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Attach", fieldname:"item_img_4", label:"Attach Image..."},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_group_4", options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_uom_4", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_5", label:"Item 5", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Attach", fieldname:"item_img_5", label:"Attach Image..."},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_group_5", options:["Products", "Services", "Raw Material", "Sub Assemblies"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_uom_5", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
				],
			},

			// Suppliers
			{
				icon: "icon-group",
				"title": wn._("Your Suppliers"),
				"help": wn._("List a few of your suppliers. They could be organizations or individuals."),
				"fields": [
					{fieldtype:"Data", fieldname:"supplier_1", label:"Supplier 1", placeholder:"Supplier Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"supplier_contact_1", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"supplier_2", label:"Supplier 2", placeholder:"Supplier Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"supplier_contact_2", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"supplier_3", label:"Supplier 3", placeholder:"Supplier Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"supplier_contact_3", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"supplier_4", label:"Supplier 4", placeholder:"Supplier Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"supplier_contact_4", label:"", placeholder:"Contact Name"},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"supplier_5", label:"Supplier 5", placeholder:"Supplier Name"},
					{fieldtype:"Column Break"},
					{fieldtype:"Data", fieldname:"supplier_contact_5", label:"", placeholder:"Contact Name"},
				],
			},

			// Items to Buy
			{
				icon: "icon-barcode",
				"title": wn._("Products or Services You Buy"),
				"help": wn._("List a few products or services you buy from your suppliers or vendors. If these are same as your products, then do not add them."),
				"fields": [
					{fieldtype:"Data", fieldname:"item_buy_1", label:"Item 1", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_group_1", options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_uom_1", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_buy_2", label:"Item 2", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_group_2", options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_uom_2", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_buy_3", label:"Item 3", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_group_3", options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_uom_3", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_buy_4", label:"Item 4", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_group_4", options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_uom_4", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
					{fieldtype:"Section Break"},
					{fieldtype:"Data", fieldname:"item_buy_5", label:"Item 5", placeholder:"A Product or Service"},
					{fieldtype:"Column Break"},
					{fieldtype:"Section Break"},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_group_5", options:["Raw Material", "Consumable", "Sub Assemblies", "Services", "Products"]},
					{fieldtype:"Column Break"},
					{fieldtype:"Select", fieldname:"item_buy_uom_5", options:["Unit", "Nos", "Box", "Pair", "Kg", "Set", "Hour", "Minute"]},
				],
			},

		]
		
	})
}

wn.pages['setup-wizard'].onshow = function(wrapper) {
	if(wn.get_route()[1])
		erpnext.wiz.show(wn.get_route()[1]);
}

wn.provide("wn.wiz");

wn.wiz.Wizard = Class.extend({
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
			'<br><p class="text-center"><button class="btn btn-primary">'+wn._("Start")+'</button></p>')
			.appendTo(this.parent);
		
		this.$welcome.find(".btn").click(function() {
			me.$welcome.toggle(false);
			me.welcomed = true;
			wn.set_route(me.page_name, "0");
		})
		
		this.current_slide = {"$wrapper": this.$welcome};
	},
	show_working: function() {
		this.hide_current_slide();
		wn.set_route(this.page_name);
		this.current_slide = {"$wrapper": this.get_message(this.working_html).appendTo(this.parent)};
	},
	show_complete: function() {
		this.hide_current_slide();
		this.current_slide = {"$wrapper": this.get_message(this.complete_html).appendTo(this.parent)};
	},
	show: function(id) {
		if(!this.welcomed) {
			wn.set_route(this.page_name);
			return;
		}
		id = cint(id);
		if(this.current_slide && this.current_slide.id===id) 
			return;
		if(!this.slide_dict[id]) {
			this.slide_dict[id] = new wn.wiz.WizardSlide($.extend(this.slides[id], {wiz:this, id:id}));
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

wn.wiz.WizardSlide = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
	},
	make: function() {
		var me = this;
		this.$wrapper = $(repl('<div class="panel panel-default">\
			<div class="panel-heading"><div class="panel-title">%(main_title)s: Step %(step)s</div></div>\
			<div class="panel-body">\
				<div class="progress">\
					<div class="progress-bar" style="width: %(width)s%"></div>\
				</div>\
				<br>\
				<div class="row">\
					<div class="col-sm-8 form"></div>\
					<div class="col-sm-4 help">\
						<h3 style="margin-top: 0px"><i class="%(icon)s text-muted"></i> %(title)s</h3><br>\
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
			this.form = new wn.ui.FieldGroup({
				fields: this.fields,
				body: this.body,
				no_submit_on_enter: true
			});
			this.form.make();
		} else {
			$(this.body).html(this.html)
		}
		
		if(this.id > 0) {
			this.$prev = $("<button class='btn btn-default'>Previous</button>")
				.click(function() { 
					wn.set_route(me.wiz.page_name, me.id-1 + ""); 
				})
				.appendTo(this.$wrapper.find(".footer"))
				.css({"margin-right": "5px"});
			}
		if(this.id+1 < this.wiz.slides.length) {
			this.$next = $("<button class='btn btn-primary'>Next</button>")
				.click(function() { 
					me.values = me.form.get_values();
					if(me.values===null) 
						return;
					wn.set_route(me.wiz.page_name, me.id+1 + ""); 
				})
				.appendTo(this.$wrapper.find(".footer"));
		} else {
			this.$complete = $("<button class='btn btn-primary'>Complete Setup</button>")
				.click(function() { 
					me.values = me.form.get_values();
					if(me.values===null) 
						return;
					me.wiz.on_complete(me.wiz); 
				}).appendTo(this.$wrapper.find(".footer"));
		}
		
		if(this.onload) {
			this.onload(this);
		}

	},
	get_input: function(fn) {
		return this.form.get_input(fn);
	}
})