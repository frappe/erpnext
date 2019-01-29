<template>
	<p class="text-muted" v-html="header_item"></p>
</template>

<script>

const spacer = '<span aria-hidden="true"> · </span>';

export default {
	name: 'detail-header-item',
	props: ['value'],
	data() {
		return {
			header_item: Array.isArray(this.value)
				? this.value.join(spacer)
				: this.value
		}
	},
}
</script>
