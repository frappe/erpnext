<template>
	<div class="empty-state flex flex-column"
		:class="{ 'bordered': bordered, 'align-center': centered, 'justify-center': centered }"
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
		action: Object,
		centered: {
			type: Boolean,
			default: true
		}
	}
}
</script>

<style lang="less">
	@import "../../../../../../frappe/frappe/public/less/variables.less";
	.empty-state {
		height: 150px;
	}
	.empty-state.bordered {
		border-radius: 4px;
		border: 1px solid @border-color;
		border-style: dashed;
		// bad, due to item card column layout, that is inner 15px margin
		margin: 0 15px;
	}
</style>