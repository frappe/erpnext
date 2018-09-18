<template>
	<div class="hub-list-item" :data-route="item.route">
		<div class="hub-list-left">
			<base-image class="hub-list-image" :src="item.image" />
			<div class="hub-list-body ellipsis">
				<div class="hub-list-title">{{item.item_name}}</div>
				<div class="hub-list-subtitle ellipsis">
					<slot name="subtitle"></slot>
				</div>
			</div>
		</div>
		<div class="hub-list-right" v-if="message">
			<span class="text-muted" v-html="frappe.datetime.comment_when(message.creation, true)" />
		</div>
	</div>
</template>
<script>
export default {
	props: ['item', 'message']
}
</script>
