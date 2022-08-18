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
						<span class="abbreviation-text">TV</span>
					</div>
					<div class="col-8 company-name">
						Your Company Name
					</div>
					<div class="button-container">
						<div class="btn edit-button btn-secondary">
							<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2" stroke="#505A62" stroke-linecap="round"/>
								<path d="M14 2L7 9" stroke="#505A62" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
							&nbsp;&nbsp;Edit
						</div>
					</div>
				</div>
				<div class="company-domain">
					<div>
						What does your organization do?
					</div>
					<div class="row domain-box">
						<div class="domain"
						v-bind:class="[selectedDomain == domain ? 'selected-domain' :'']"
						@click="selectedDomain = domain"
						v-for="(domain, index) in domains" :key="index">
							{{ domain }}
						</div>
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
			<div v-show="CurrentStep == 4" class="row module-layout">
				<Module v-for="(module, index) in modules" :key="index" :module="module" />
			</div>
			<div class="row button-row">
				<div>
					<button v-on:click=prev_step class="btn btn-secondary btn-sm" v-if="CurrentStep > 1">Previous</button>
				</div>
				<div>
					<button v-on:click=next_step class="btn btn-primary btn-sm btn-next" v-if="CurrentStep < 4">Next</button>
					<button class="btn btn-primary btn-sm btn-next" v-if="CurrentStep == 4">Finish Setup</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import Module from "./Module.vue";
frappe.provide('frappe.setup');

export default {
	name: 'Onboarding',
	props: ["modules", "regional_data"],
	data() {
		return {
			CurrentStep: 1,
			selectedDomain: '',
			steps: {
				1: "Setup Organization",
				2: "Regional Settings",
				3: "Accounting Setup",
				4: "Enabled Module"
			},
			domains: ["Manufacturing", "Retail", "Service", "Distribution", "Loans"],
		};
	},
	components: {
		Module,
	},
	methods: {
		next_step: function (event) {
			this.CurrentStep += 1;
		},
		prev_step: function(event) {
			this.CurrentStep -= 1;
		}
	},
	mounted() {
		// console.log(this.regional_data);
		let regional_data = this.regional_data.country_info;
		// console.log(regional_data);
		this.slide_2 = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __('Your Country'),
					fieldname: 'country',
					fieldtype: 'Link',
					placeholder: __("Select Country"),
					options: "Country",
					reqd: 1,
					onchange: () => {
						let country = this.slide_2.get_value('country');
						this.slide_2.set_value("currency", regional_data[country].currency);
						this.slide_2.set_value("timezone", regional_data[country].timezones[0]);
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
					reqd: 1,
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
					reqd: 1,
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
					reqd: 1
				},
				{
					label: __('Timezone'),
					fieldname: 'timezone',
					fieldtype: 'Select',
					placeholder: __("Select Time Zone"),
					options: this.regional_data.all_timezones,
					reqd: 1
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

			],
			body: this.$refs.slide_3
		});

		this.slide_3.make();
	}
}
</script>

<style scoped>
.onboarding-container {
	height: 800px;
	background: #FFFFFF;
	border-radius: 16px;
}

.onboarding-sidebar {
	height: 100%;
	background: #F0F0F0;
	border-radius: 16px;
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
	height: 600px;
	padding:40px;
	gap: 16px;
	justify-content: center;
	overflow: scroll;
	scrollbar-width: 'none';
	-ms-overflow-style: 'none'
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
}

.domain-box {
	margin-top: 8px;
}

.selected-domain {
	background: #687178;
	color: #FFFFFF !important;
}
</style>