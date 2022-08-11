<template>
		<div class="module-body">
			<div>
				<div>
					<div>
						<input class="module-checkbox" type="checkbox" v-model="checked">
					</div>
					<div class="icon">
						<span class="icon-container" v-html="getIcon"></span>
					</div>

				</div>
				<p class="module-title">{{ module.name }}</p>
				<p class="module-subtitle">
					Products, Purchases, <br />Analysis, and more.
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
	props: ["module"],
	methods: {
		toggle() {
			this.$emit('toggle', this.checked);
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
.module-body {
	height: 160px;
	width: 280px;
	background: #F5FAFF;
	border-radius: 10px;
}

.icon {
	margin-top: 15px;
}

.icon-container {
	display: flex;
	box-sizing: border-box;
	width: 42px;
	height: 42px;
	background: #EBF4FC;
	border: 1px solid #DEEEFC;
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
	margin-top: 10px;
}
</style>