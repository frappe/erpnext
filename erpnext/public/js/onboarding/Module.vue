<template>
		<div v-on:click=toggle class="module-body"
			v-bind:class="[primary ? 'primary-module':'', checked ? 'checked-border':'']">
			<div>
				<input class="module-checkbox" type="checkbox" v-model="checked">
				<div class="icon">
					<div class="icon-container"
					v-bind:class="[primary ? 'primary-icon' :'']"
					v-html="getIcon"></div>
				</div>
				<p class="module-title">{{ module.name }}</p>
				<p class="module-subtitle">
					{{ module.description }}
				</p>
			</div>
		</div>
</template>

<script>

export default {
	name: 'Module',
	data() {
		return {
			checked: false,
		};
	},
	props: ["module", "primary"],
	methods: {
		toggle() {
			this.checked = !this.checked;
			this.$emit('toggle', this.module.name, this.checked);
		},
	},
	computed: {
		getIcon: function () {
			let icon = "#icon-" + this.module.icon;
			return `<svg><use href="${icon}"></use></svg>`
		}
	}
}
</script>

<style scoped>

.primary-module {
	background: #F5FAFF !important;
}

.module-body {
	cursor: pointer;
	height: 160px;
	width: 250px;
	border-radius: 10px;
	box-shadow: 0px 2px 6px rgba(17, 43, 66, 0.08), 0px 1px 4px rgba(17, 43, 66, 0.1);
	padding-right: 10px;
}

.checked-border {
	border: 1px solid #2D95F0 !important;
}

.primary-icon {
	background: #EBF4FC !important;
	border: 1px solid #DEEEFC !important;
}

.icon {
	margin-top: 15px;
}

.icon-container {
	display: flex;
	box-sizing: border-box;
	width: 42px;
	height: 42px;
	padding: 5px;
	background: #F4F5F6;
	border: 1px solid #EBEEF0;
	border-radius: 6px;
}

.module-title {
	font-family: 'Inter';
	font-style: normal;
	font-weight: 500;
	font-size: 1.2em;
	margin-top: 25px;
}

.module-subtitle {
	width: 194px;
	font-family: 'Inter';
	font-style: normal;
	font-weight: 400;
	font-size: 1em;
	line-height: 15px;
	color: #505A62
}

.module-checkbox {
	float: right;
	margin-top: 12px;
}
</style>