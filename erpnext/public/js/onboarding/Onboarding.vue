<template>
	<div class="layout-main-section row onboarding-container">
		<div class="col-3 onboarding-sidebar">
			<div class="sidebar-container">
				<div class="step-title row" v-for="(step, index) in steps" :key="index">
					<div class="step-no" v-bind:class="[CurrentStep == index ? 'current-step' :'', CurrentStep > index ? 'completed-step': '']">
						<svg v-if="CurrentStep > index" class="icon icon-xs completed-step">
							<use class="" href="#icon-tick"></use>
						</svg>
						<p v-else style="margin-top:2px">{{ index }}</p>
					</div>
					<span class="step" v-bind:class="[CurrentStep == index ? 'current-step' :'']">{{ step }}</span>
				</div>
			</div>
		</div>
		<div class="slide-section col-9">
			<div v-show="CurrentStep == 1">
				<p class="onboarding-title">Setup Organization</p>
				<p class="onboarding-subtitle">Don't Panic - These settings can be changed later.</p>
				<div class="row company-info">
					<div class="abbreviation-container">
						<span class="abbreviation-text">{{ abbreviation }}</span>
					</div>
					<input class="input-field col-6" v-if="edit" v-model="company_name">
					<div v-if="!edit" class="col-8 company-name">
						{{ company_name }}
					</div>
					<div class="button-container">
						<div v-on:click="toggle_edit"
							class="btn edit-button btn-secondary">
							<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2" stroke="#505A62" stroke-linecap="round"/>
								<path d="M14 2L7 9" stroke="#505A62" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
							&nbsp;&nbsp;{{ button_string }}
						</div>
					</div>
				</div>
				<div class="company-domain">
					<div>
						What does your organization do?
					</div>
					<div class="row domain-box">
						<button class="domain"
							@click="selectedDomain = domain"
							:class="[selectedDomain == domain ? 'selected-domain' :'']"
							v-for="(domain, index) in domains" :key="index"
						>
							{{ domain }}
						</button>
					</div>
				</div>
			</div>
			<div v-show="CurrentStep == 2">
				<p class="onboarding-title">Regional Settings</p>
				<p class="onboarding-subtitle">Don't Panic - These settings can be changed later.</p>
				<div class="field-layout" ref="slide_2">
				</div>
			</div>
			<div v-show="CurrentStep == 3">
				<p class="onboarding-title">Accounting Setup</p>
				<p class="onboarding-subtitle">Don't Panic - These settings can be changed later.</p>
				<div class="field-layout" ref="slide_3">
				</div>
			</div>
			<div v-show="CurrentStep == 4">
				<p class="onboarding-title">Enable Modules</p>
				<p class="onboarding-subtitle">Think of modules as apps that you might need for your org</p>
			</div>
			<div v-show="CurrentStep == 4" class="module-layout">
				<div>
					<div class="row module-row">
						<Module v-for="(module, index) in modules.slice(0, 3)" :key="index" :module="module" :primary=1
						v-on:toggle="add_remove_module" />
						<Module v-for="(module, index) in modules.slice(3, 6)" :key="index + 3" :module="module" :primary=0
						v-on:toggle="add_remove_module" />
					</div>
				</div>
				<div>
					<div class="section-heading">
						Others
					</div>
					<div class="row module-row">
						<Module v-for="(module, index) in modules.slice(6, -1)" :key="index + 6" :module="module" :primary=0
						v-on:toggle="add_remove_module" />
					</div>
				</div>
			</div>
			<div class="row button-row">
				<div>
					<button v-on:click=prev_step class="btn btn-secondary btn-sm" v-if="CurrentStep > 1">Previous</button>
				</div>
				<div>
					<button v-on:click=next_step class="btn btn-primary btn-sm btn-next" v-if="CurrentStep < 4">Next</button>
					<button v-on:click=finish_setup class="btn btn-primary btn-sm btn-next" v-if="CurrentStep == 4">Finish Setup</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import Module from "./Module.vue";
import LoadingIndicator from './LoadingIndicator.vue'
frappe.provide('frappe.setup');

export default {
	name: 'Onboarding',
	props: ["modules", "regional_data"],
	data() {
		return {
			CurrentStep: 1,
			selectedDomain: '',
			company_name: "My Company",
			abbreviation: "MC",
			edit: false,
			button_string: "Edit",
			steps: {
				1: "Setup Organization",
				2: "Regional Settings",
				3: "Accounting Setup",
				4: "Enabled Module"
			},
			domains: ["Manufacturing", "Retail", "Service", "Distribution", "Loans", "Education", "Healthcare", "Other"],
			fiscal_years: {
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
			},
			enabled_modules: [],
		};
	},
	components: {
		Module,
		LoadingIndicator
	},
	methods: {
		next_step: function () {
			let slide = "slide_" + this.CurrentStep;
			let missing = 0;

			if (this[slide]) {
				Object.keys(this[slide].fields_dict).forEach((fieldname) => {
					let field = this[slide].get_field(fieldname).df;
					if (!["Section Break", "Column Break"].includes(field.fieldtype) && !this[slide].get_value(fieldname)) {
						this[slide].set_df_property(fieldname, "reqd", field.label + " is mandatpry");
						this[slide].set_df_property(fieldname, "description", field.label + " is mandatory");
						missing = 1;
					}
				});
			}

			if (!missing) {
				this.CurrentStep += 1;
			}
		},
		prev_step: function() {
			this.CurrentStep -= 1;
		},
		toggle_edit: function() {
			this.edit = !this.edit;
			this.button_string = this.edit ? "Save" : "Edit";

			let parts = this.company_name.split(" ");
			let abbr = $.map(parts, function (p) { return p ? p.substr(0, 1) : null }).join("");
			this.abbreviation=abbr.slice(0, 10).toUpperCase();
		},
		finish_setup: function() {
			console.log(this.enabled_modules);
			// frappe.throw("Finish Setup");
			frappe.call({
				method: "frappe.desk.page.setup_wizard.setup_wizard.setup_complete",
				args: { args: {
					"company_name": this.company_name,
					"company_abbreviation": this.abbreviation,
					"currency": this.slide_2.get_value("currency"),
					"country": this.slide_2.get_value("country"),
					"timezone": this.slide_2.get_value("timezone"),
					"fy_start_date": this.slide_3.get_value("fy_start_date"),
					"fy_end_date": this.slide_3.get_value("fy_end_date"),
					"chart_of_accounts": this.slide_3.get_value("chart_of_accounts"),
					"bank_account": this.slide_3.get_value("bank_account"),
					"domain": this.selectedDomain,
					"company_tagline": this.slide_3.get_value("tagline"),
					"enabled_modules": this.enabled_modules,
				}},
				callback: (r) => {
					if (r.message.status === "ok") {
						if (frappe.setup.welcome_page) {
								localStorage.setItem("session_last_route", frappe.setup.welcome_page);
							}
							setTimeout(function () {
								// Reload
								window.location.href = "/app";
							}, 2000);
					}
				},
				error: () => frappe.msgprint(__("Something went wrong")),
			});
		},
		add_remove_module: function(module, checked) {
			if (checked) {
				this.enabled_modules.push(module);
			} else {
				let index = this.enabled_modules.indexOf(module);
				if (index !== -1) {
					this.enabled_modules.splice(index, 1);
				}
			}
		}
	},
	mounted() {
		let regional_data = this.regional_data.country_info;
		this.slide_2 = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __('Your Country'),
					fieldname: 'country',
					fieldtype: 'Link',
					placeholder: __("Select Country"),
					options: "Country",
					only_select: true,
					onchange: () => {
						let country = this.slide_2.get_value('country');
						if (country) {
							frappe.call({
								method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
								args: { "country": country, with_standard: true },
								callback: (r) => {
									if (r.message) {
										this.slide_3.set_df_property("chart_of_accounts", "options", r.message)
									}
								}
							})
						}
						this.slide_2.set_value("currency", regional_data[country].currency);
						this.slide_2.set_value("timezone", regional_data[country].timezones[0]);

						let fy = this.fiscal_years[country];
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

						this.slide_3.set_value("fy_start_date", current_year + '-' + fy[0]);
						this.slide_3.set_value("fy_end_date", next_year + '-' + fy[1]);
					}
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
				},
				{
					label: __('Currency'),
					fieldname: 'currency',
					fieldtype: 'Link',
					options: 'Currency',
					only_select: true,
				},
				{
					label: '',
					fieldname: 'sb_1',
					fieldtype: 'Section Break',
				},
				{
					fieldname: "language",
					label: __("Your Language"),
					fieldtype: "Link",
					placeholder: __("Select Language"),
					default: "en",
					options: "Language",
					only_select: true,
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
				},
				{
					label: __('Timezone'),
					fieldname: 'timezone',
					fieldtype: 'Select',
					placeholder: __("Select Time Zone"),
					options: this.regional_data.all_timezones,
				},

			],
			body: this.$refs.slide_2
		});

		this.slide_2.make();

		this.slide_3 = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __('Bank Name'),
					fieldname: 'bank_name',
					fieldtype: 'Data',
					placeholder: __("Add Your Bank Name"),
					reqd: 1,
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
				},
				{
					label: __('Chart Of Accounts'),
					fieldname: 'chart_of_accounts',
					fieldtype: 'Select',
					options: [],
					reqd: 1,
				},
				{
					label: '',
					fieldname: 'sb_1',
					fieldtype: 'Section Break',
				},
				{
					fieldname: "fy_start_date",
					label: __("Financial Year Begins On"),
					fieldtype: "Date",
					reqd: 1,
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
					reqd: 1
				},
				{
					fieldname: "fy_end_date",
					label: __("Financial Year Ends On"),
					fieldtype: "Date",
					reqd: 1,
				},
				{
					label: '',
					fieldname: 'sb_2',
					fieldtype: 'Section Break',
				},
				{
					fieldname: "tagline",
					label: __("Company Tagline"),
					fieldtype: "Data",
					reqd: 1,
				},

			],
			body: this.$refs.slide_3
		});

		this.slide_3.make();
	}
}
</script>

<style scoped>
.onboarding-container {
	margin-top: 50px;
	height: 650px;
	background: #FFFFFF;
	border-radius: 16px;
}

.onboarding-sidebar {
	height: 100%;
	background: #F0F0F0;
	border-radius: 16px 0 0 16px;
}

.onboarding-title {
	font-family: 'Inter';
	font-style: normal;
	font-weight: 700;
	font-size: 24px;
	line-height: 29px;
	text-align: center;
	letter-spacing: -0.2px;
	color: #1F272E;
	margin-top: 40px;
}

.onboarding-subtitle {
	font-family: 'Inter';
	font-style: normal;
	font-weight: 400;
	font-size: 13px;
	line-height: 20px;
	text-align: center;
	font-feature-settings: 'case' on;
	color: #505A62;
}

.module-layout {
	height: 450px;
	justify-content: center;
	overflow: scroll;
	scrollbar-width: 'none';
	-ms-overflow-style: 'none'
}

.module-row {
	gap: 16px;
	margin-left: 40px;
}

.section-heading {
	font-weight: 600;
	font-size: 16px;
	line-height: 24px;
	margin-left: 40px;
	margin-top: 17px;
	margin-bottom: 12px;
}

.slide-section {
	height: 100%;
}

.step-title {
	height: 20px;
	font-family: 'Inter';
	font-weight: 500;
	color: #505A62;
	margin-top: 16px;
}

.step-no {
	box-sizing: border-box;
	background: #FFFFFF;
	border: 1px solid #EBEEF0;
	border-radius: 50%;
	width: 28px;
	height: 28px;
	color: #505A62;
	text-align: center;
	margin-right: 12px;
}

.sidebar-container {
	margin-left: 30px;
	margin-top:30px
}

.step {
	margin-top: 3px;
}

.label {
	width: 262px;
	height: 15px;
	font-family: 'Inter';
	font-style: normal;
	font-weight: 400;
	font-size: 12px;
	line-height: 15px;
	color: #505A62;
	mix-blend-mode: normal;
	flex: none;
	order: 0;
	align-self: stretch;
	flex-grow: 0;
}

.field-layout {
	margin-top: 50px;
	margin-left: 40px;
	margin-right: 40px;
}

.button-row {
	width: 100%;
	position: absolute;
	padding-left: 75px;
	padding-right: 75px;
	bottom: 50px;
	justify-content: space-between;
}

::-webkit-scrollbar {
	display: none;
}

.completed-step {
	background-color: #48BB74;
	stroke: white;
}

.current-step {
	color: #2D95F0;
	border-color: #2D95F0;
}

.abbreviation-container {
	display: flex;
	width: 72px;
	height: 72px;
	background: #EBEEF0;
	border-radius: 8px;
	align-items: center;
	justify-content: center;
}

.abbreviation-text {
	font-weight: 600;
	font-size: 28px;
	line-height: 34px;
	text-align: center;
	color: #1F272E;
	opacity: 0.5;
	margin:0;
}

.company-info {
	margin-left: 82px;
	margin-top: 67px;
}

.company-name {
	display: flex;
	font-family: 'Inter';
	font-style: normal;
	font-weight: 600;
	font-size: 25px;
	line-height: 25px;
	color: #1F272E;
	align-items: center;
}

.edit-button {
	display: flex;
	height: 28px;
	align-items: center;
}

.button-container {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.company-domain {
	margin-left: 82px;
	margin-top: 70px;

}

.domain {
	box-sizing: border-box;
	display: flex;
	flex-direction: row;
	align-items: flex-start;
	padding: 8px 14px;
	gap: 10px;
	border: 1px solid #EBEEF0;
	border-radius: 8px;
	margin-left: 9px;
	background-color:#FFFFFF;
}

.domain-box {
	margin-top: 8px;
}

.selected-domain {
	background: #687178;
	color: #FFFFFF !important;
}

.input-field {
	background: #F4F5F6;
	border-radius: 8px;
	flex: none;
	order: 1;
	align-self: stretch;
	flex-grow: 1;
}
</style>