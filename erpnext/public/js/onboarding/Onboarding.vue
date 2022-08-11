<template>
	<div class="layout-main-section row onboarding-container">
		<div class="col-3 onboarding-sidebar">
			<div class="sidebar-container">
				<div class="step-title row" v-for="(step, index) in steps" :key="index">
					<div class="step-no">
						<p style="margin-top:2px">{{ index }}</p>
					</div>
					<span class="step">{{ step }}</span>
				</div>
			</div>
		</div>
		<div class="slide-section col-9">
			<div v-show="CurrentStep == 1">
				<p class="onboarding-title">Setup Organization</p>
				<p class="onboarding-subtitle">Don't Panic - These settings can be changed later.</p>
				<div class="row field-row">
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
				<div class="button-col">
					<button v-on:click="CurrentStep -= 1" class="secondary-button" v-if="CurrentStep > 1">Previous</button>
				</div>
				<div class="button-col">
					<button v-on:click="CurrentStep += 1" class="primary-button" v-if="CurrentStep < 4">Next</button>
					<button class="primary-button" v-if="CurrentStep == 4">Complete Setup</button>
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
			steps: {
				1: "Setup Organization",
				2: "Regional Settings",
				3: "Accounting Setup",
				4: "Enabled Module"
			}
		};
	},
	components: {
		Module,
	},
	mounted() {
		let regional_data = this.regional_data.country_info;
		console.log(regional_data);
		const slide_2 = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __('Country'),
					fieldname: 'country',
					fieldtype: 'Autocomplete',
					placeholder: __("Select Country"),
					onchange: () => {
						let country = slide_2.get_value('country');
						slide_2.set_value("currency", regional_data[country].currency);
						slide_2.set_value("timezone", regional_data[country].timezones[0]);
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
				},
				{
					label: '',
					fieldname: 'sb_1',
					fieldtype: 'Section Break',
				},
				{
					label: __('Language'),
					fieldname: 'language',
					fieldtype: 'Autocomplete',
					options: 'Language',
					default: 'English'
				},
				{
					label: '',
					fieldname: 'cb_1',
					fieldtype: 'Column Break',
				},
				{
					label: __('Timezone'),
					fieldname: 'timezone',
					fieldtype: 'Data',
				},

			],
			body: this.$refs.slide_2
		});

		slide_2.make();
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
	background: #F9FAFA;
	border: 1px solid #E5E5E5;
}

.onboarding-title {
	/* position: absolute;
	display: flex; */
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

.secondary-button {
	display: block;
	align-items: center;
	text-align: center;
	padding: 4px 20px;
	height: 28px;
	background: #F9FAFA;
	border-radius: 8px;
	color: #687178;
	border: 0px;
	float: left;
}
.primary-button {
	align-items: center;
	text-align: center;
	padding: 4px 20px;
	height: 28px;
	background: #2D95F0;
	border-radius: 8px;
	color: #FFFFFF;
	border: 0px;
	float: right;
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

.control-input {
	background: #F4F5F6;
	border-radius: 8px;
	flex: none;
	height: 28px;
	order: 1;
	align-self: stretch;
	flex-grow: 1;
	border: 0px;
	width: 100%;
}

.field-layout {
	margin-top: 50px;
	margin-left: 40px;
	margin-right: 40px;
}

.field-row {
	margin-top: 24px;
}

.button-row {
	margin-left: 40px;
	margin-right: 40px;
}

.button-col {
	margin: 0px;
	padding: 0px;
}

.control-input-wrapper {
	width:100% !important;
}

::-webkit-scrollbar {
	display: none;
}

</style>