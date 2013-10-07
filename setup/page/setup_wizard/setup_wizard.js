wn.pages['setup-wizard'].onload = function(wrapper) { 
	$(".navbar:first").toggle(false);
	
	erpnext.wiz = new wn.wiz.Wizard({
		parent: wrapper,
		title: wn._("ERPNext Setup Guide"),
		slides: [
			// User
			{
				title: wn._("The First User: You"),
				icon: "icon-user",
				fields: [
					{"fieldname": "first_name", "label": wn._("First Name"), "fieldtype": "Data", reqd:1},
					{"fieldname": "last_name", "label": wn._("Last Name"), "fieldtype": "Data", reqd:1},
					{fieldtype:"Attach Image", fieldname:"attach_profile", label:"Attach Your Profile..."},
				],
				help: wn._('The first user will become the System Manager (you can change that later).')
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
					{fieldname:'company_tagline', label: wn._('What does it do?'), fieldtype:'Data',
						placeholder:'e.g. "Build tools for builders"',reqd:1},
				],
				help: wn._('The name of your company for which you are setting up this system.'),
				onload: function(slide) {
					slide.get_input("company_name").on("change", function() {
						var parts = slide.get_input("company_name").val().split(" ");
						var abbr = $.map(parts, function(p) { return p ? p.substr(0,1) : null }).join("");
						slide.get_input("company_abbr").val(abbr.toUpperCase());
					});
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
				// html: '<h4>' + wn._('Upload Logo') + '</h4><div class="upload-area-letter-head"></div><hr>'
				// 	+'<h4>' + wn._('Upload Letter Head') + '</h4><div class="upload-area-logo"></div>',
				onload: function(slide) {
					// wn.upload.make({
					// 	parent: slide.$wrapper.find(".upload-area-letter-head").css({"margin-left": "10px"}),
					// 	on_attach: function(fileobj) {
					// 		console.log(fileobj);
					// 	}
					// });
					// 
					// wn.upload.make({
					// 	parent: slide.$wrapper.find(".upload-area-logo").css({"margin-left": "10px"}),
					// 	on_attach: function(fileobj) {
					// 		console.log(fileobj);
					// 	}
					// });
				}
				
			},
			
			// Taxes
			{
				icon: "icon-money",
				"title": wn._("Add Taxes"),
				"help": wn._("List your tax heads (e.g. VAT, Excise) (upto 3) and their standard rates. This will create a standard template, you can edit and add more later."),
				"fields": [
					{fieldtype:"Column Break", fieldname:"cb_1", "label": "Tax Heads"},
					{fieldtype:"Data", fieldname:"tax_1", label:"Tax 1", placeholder:"e.g. VAT"},
					{fieldtype:"Data", fieldname:"tax_2", label:"Tax 2", placeholder:"e.g. Customs Duty"},
					{fieldtype:"Data", fieldname:"tax_3", label:"Tax 3", placeholder:"e.g. Excise"},
					{fieldtype:"Column Break", fieldname:"cb_2", "label": "Tax Rates"},
					{fieldtype:"Data", fieldname:"tax_rate_1", label:"Rate (%)", placeholder:"e.g. 5"},
					{fieldtype:"Data", fieldname:"tax_rate_2", label:"Rate (%)", placeholder:"e.g. 5"},
					{fieldtype:"Data", fieldname:"tax_rate_3", label:"Rate (%)", placeholder:"e.g. 5"},
				],
				onload: function(slide) {
				}
			},
			
			// Items to Sell
			{
				icon: "icon-barcode",
				"title": wn._("Your Products or Services"),
				"help": wn._("List your products or services that you sell to your customers."),
				"fields": [
					{fieldtype:"Data", fieldname:"item_1", label:"Item 1", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_2", label:"Item 2", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_3", label:"Item 3", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_4", label:"Item 4", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_5", label:"Item 5", placeholder:"A Product or Service"},
					{fieldtype:"Column Break", fieldname:"cb_2", "label": "Attachments"},
					{fieldtype:"Attach", fieldname:"item_img_1", label:"Attach Image..."},
					{fieldtype:"Attach", fieldname:"item_img_2", label:"Attach Image..."},
					{fieldtype:"Attach", fieldname:"item_img_3", label:"Attach Image..."},
					{fieldtype:"Attach", fieldname:"item_img_4", label:"Attach Image..."},
					{fieldtype:"Attach", fieldname:"item_img_5", label:"Attach Image..."},
				],
				onload: function(slide) {
				}
			},

			// Items to Buy
			{
				icon: "icon-barcode",
				"title": wn._("Products or Services You Buy"),
				"help": wn._("List a few products or services you buy from your suppliers or vendors. If these are same as your products, then do not add them."),
				"fields": [
					{fieldtype:"Data", fieldname:"item_buy_1", label:"Item 1", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_buy_2", label:"Item 2", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_buy_3", label:"Item 3", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_buy_4", label:"Item 4", placeholder:"A Product or Service"},
					{fieldtype:"Data", fieldname:"item_buy_5", label:"Item 5", placeholder:"A Product or Service"},
				],
				onload: function(slide) {
				}
			},

			// Customers
			{
				icon: "icon-group",
				"title": wn._("Your Customers"),
				"help": wn._("List a few of your customers. They could be organizations or individuals."),
				"fields": [
					{fieldtype:"Data", fieldname:"customer_1", label:"Customer 1", placeholder:"Customer Name"},
					{fieldtype:"Data", fieldname:"customer_2", label:"Customer 2", placeholder:"Customer Name"},
					{fieldtype:"Data", fieldname:"customer_3", label:"Customer 3", placeholder:"Customer Name"},
					{fieldtype:"Data", fieldname:"customer_4", label:"Customer 4", placeholder:"Customer Name"},
					{fieldtype:"Data", fieldname:"customer_5", label:"Customer 5", placeholder:"Customer Name"},
				],
				onload: function(slide) {
				}
			},

			// Suppliers
			{
				icon: "icon-group",
				"title": wn._("Your Suppliers"),
				"help": wn._("List a few of your suppliers. They could be organizations or individuals."),
				"fields": [
					{fieldtype:"Data", fieldname:"supplier_1", label:"Supplier 1", placeholder:"Supplier Name"},
					{fieldtype:"Data", fieldname:"supplier_2", label:"Supplier 2", placeholder:"Supplier Name"},
					{fieldtype:"Data", fieldname:"supplier_3", label:"Supplier 3", placeholder:"Supplier Name"},
					{fieldtype:"Data", fieldname:"supplier_4", label:"Supplier 4", placeholder:"Supplier Name"},
					{fieldtype:"Data", fieldname:"supplier_5", label:"Supplier 5", placeholder:"Supplier Name"},
				],
				onload: function(slide) {
				}
			}

		]
		
	})
}

wn.pages['setup-wizard'].onshow = function(wrapper) {
	erpnext.wiz.show(wn.get_route()[1] || "0");
}

wn.provide("wn.wiz");

wn.wiz.Wizard = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.slide_dict = {};
		wn.set_route("setup-wizard", "0");
	},
	show: function(id) {
		id = cint(id);
		if(this.current_slide && this.current_slide.id===id) 
			return;
		if(!this.slide_dict[id]) {
			this.slide_dict[id] = new wn.wiz.WizardSlide($.extend(this.slides[id], {wiz:this, id:id}));
			this.slide_dict[id].make();
		}
		
		if(this.current_slide)
			this.current_slide.$wrapper.toggle(false);
		
		this.current_slide = this.slide_dict[id];
		this.current_slide.$wrapper.toggle(true);
	},
});

wn.wiz.WizardSlide = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
	},
	make: function() {
		var me = this;
		this.$wrapper = $(repl('<div class="panel panel-default" style="margin: 0px 30px;">\
			<div class="panel-heading"><div class="panel-title">%(main_title)s: Step %(step)s</div></div>\
			<div class="panel-body">\
				<div class="progress">\
					<div class="progress-bar" style="width: %(width)s%"></div>\
				</div>\
				<h3><i class="%(icon)s text-muted"></i> %(title)s</h3><br>\
				<div class="row">\
					<div class="col-sm-6 form"></div>\
					<div class="col-sm-6 help"><p class="text-muted">%(help)s</p></div>\
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
				.click(function() { wn.set_route("setup-wizard", me.id-1 + ""); })
				.appendTo(this.$wrapper.find(".footer"))
				.css({"margin-right": "5px"});
			}
		if(this.id+1 < this.wiz.slides.length) {
			this.$next = $("<button class='btn btn-primary'>Next</button>")
				.click(function() { wn.set_route("setup-wizard", me.id+1 + ""); })
				.appendTo(this.$wrapper.find(".footer"));
		} else {
			this.$complete = $("<button class='btn btn-primary'>Complete Setup</button>")
				.click(function() { me.wiz.complete(); }).appendTo(this.$wrapper.find(".footer"));
		}
		
		if(this.onload) {
			this.onload(this);
		}

	},
	get_input: function(fn) {
		return this.form.get_input(fn);
	}
})