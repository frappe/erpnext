<template>
	<div class="empty-state flex align-center flex-column justify-center"
		:class="{ bordered: bordered }"
		:style="{ height: height + 'px' }"
	>
		<p class="text-muted">{{ message }}</p>
	</div>
</template>

<script>

export default {
	name: 'empty-state',
	props: {
		message: String,
		bordered: Boolean,
		height: Number,
		// action: Function
	}
}
</script>

<style scoped></style>
