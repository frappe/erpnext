<template>
	<div v-if="item_details">
		<div>
			<a class="text-muted" v-route="back_link">← {{ __('Back to Messages') }}</a>
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
								<div style="white-space: normal;" v-html="message.message" />
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
import CommentInput from '../components/CommentInput.vue';
import ItemListCard from '../components/ItemListCard.vue';

export default {
	components: {
		CommentInput,
		ItemListCard
	},
	data() {
		return {
			message_type: frappe.get_route()[1],
			item_details: null,
			messages: []
		}
	},
	created() {
		const hub_item_name = this.get_hub_item_name();
		this.get_item_details(hub_item_name)
			.then(item_details => {
				this.item_details = item_details;
				this.get_messages()
					.then(messages => {
						this.messages = messages;
					});
			});
	},
	computed: {
		back_link() {
			return 'marketplace/' + this.message_type;
		}
	},
	methods: {
		send_message(message) {
			this.messages.push({
				sender: frappe.session.user,
				message: message,
				creation: Date.now(),
				name: frappe.utils.get_random(6)
			});
			hub.call('send_message', {
				to_seller: this.get_against_seller(),
				hub_item: this.item_details.name,
				message
			});
		},
		get_item_details(hub_item_name) {
			return hub.call('get_item_details', { hub_item_name })
		},
		get_messages() {
			if (!this.item_details) return [];
			return hub.call('get_messages', {
				against_seller: this.get_against_seller(),
				against_item: this.item_details.name
			});
		},
		get_against_seller() {
			if (this.message_type === 'buying') {
				return this.item_details.hub_seller;
			} else if (this.message_type === 'selling') {
				return frappe.get_route()[2];
			}
		},
		get_hub_item_name() {
			if (this.message_type === 'buying') {
				return frappe.get_route()[2];
			} else if (this.message_type === 'selling') {
				return frappe.get_route()[3];
			}
		}
	}
}
</script>
