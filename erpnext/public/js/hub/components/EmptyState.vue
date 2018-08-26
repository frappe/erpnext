<template>
	<div class="empty-state flex align-center flex-column justify-center"
		:class="{ bordered: bordered }"
		:style="{ height: height + 'px' }"
	>
		<p class="text-muted">{{ message }}</p>
		<p v-if="action">
			<button class="btn btn-default btn-xs"
				@click="action.on_click"
			>
				{{ action.label }}
			</button>
		</p>
	</div>
</template>

<script>

export default {
	name: 'empty-state',
	props: {
		message: String,
		bordered: Boolean,
		height: Number,
		action: Object
	}
}
</script>

<style lang="less" scoped>
	@import "../../../../../../frappe/frappe/public/less/variables.less";

	.empty-state {
		height: 500px;
		margin: 15px;
	}

	.empty-state.bordered {
		border-radius: 4px;
		border: 1px solid @border-color;
		border-style: dashed;
	}

</style>
