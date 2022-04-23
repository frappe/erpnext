<template>
	<p class="text-muted" v-if="!Array.isArray(this.header_items)" v-html="header_items"></p>
	<p class="text-muted" v-else>
		<span v-for="(header_item , index) in header_items" :key="index">
			<span v-if="index" v-html="spacer"></span>
			<span v-if="typeof(header_item) == 'string'" v-html="header_item"></span>
			<a v-else-if="typeof(header_item) == 'object'" @click="header_item.on_click(header_item.value)" v-html="header_item.value"></a>
		</span>
	</p>
</template>

<script>

const spacer = '<span aria-hidden="true"> · </span>';

export default {
	name: 'detail-header-item',
	props: ['value'],
	data() {
		return {
			header_items: this.value,
			spacer: spacer
		}
	},
}
</script>
