<template>
	<div v-if="item_details">
		<div>
			<a class="text-muted" v-route="'marketplace/buying'">← {{ __('Back to Messages') }}</a>
		</div>
		<section-header>
			<div class="flex flex-column margin-bottom">
				<h4>{{ item_details.item_name }}</h4>
				<span class="text-muted">{{ item_details.company }}</span>
			</div>
		</section-header>
		<div class="row">
			<div class="col-md-7">
				<div class="message-container">
					<div class="message-list">
						<div class="level margin-bottom" v-for="message in messages" :key="message.name">
							<div class="level-left ellipsis" style="width: 80%;">
								<div v-html="frappe.avatar(message.sender)" />
								<div style="white-space: normal;" v-html="message.content" />
							</div>
							<div class="level-right text-muted" v-html="frappe.datetime.comment_when(message.creation, true)" />
						</div>
					</div>
					<div class="message-input">
						<comment-input @change="send_message" />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import SectionHeader from '../components/SectionHeader.vue';
import CommentInput from '../components/CommentInput.vue';
import ItemListCard from '../components/ItemListCard.vue';

export default {
	components: {
		SectionHeader,
		CommentInput,
		ItemListCard
	},
	data() {
		return {
			item_details: null,
			messages: []
		}
	},
	created() {
		const hub_item_code = this.get_hub_item_code();
		this.get_item_details(hub_item_code)
			.then(item_details => {
				this.item_details = item_details;
				this.get_messages(item_details)
					.then(messages => {
						this.messages = messages;
					});
			});
	},
	methods: {
		send_message(message) {
			this.messages.push({
				sender: hub.settings.company_email,
				content: message,
				creation: Date.now(),
				name: frappe.utils.get_random(6)
			});
			hub.call('send_message', {
				from_seller: hub.settings.company_email,
				to_seller: this.item_details.hub_seller,
				hub_item: this.item_details.hub_item_code,
				message
			});
		},
		get_item_details(hub_item_code) {
			return hub.call('get_item_details', { hub_item_code })
		},
		get_messages() {
			if (!this.item_details) return [];
			return hub.call('get_messages', {
				against_seller: this.item_details.hub_seller,
				against_item: this.item_details.hub_item_code
			});
		},
		get_hub_item_code() {
			return frappe.get_route()[2];
		}
	}
}
</script>
