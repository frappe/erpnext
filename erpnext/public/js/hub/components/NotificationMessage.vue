<template>
	<div v-if="message" class="subpage-message">
        <p class="text-muted flex">
            <span v-html="message"></span>
            <i class="octicon octicon-x text-extra-muted"
                @click="$emit('remove-message')"
            >
            </i>
        </p>
    </div>
</template>

<script>

export default {
	name: 'notification-message',
	props: {
		message: String,
    }
}
</script>

<style lang="less" scoped>
    .subpage-message {
		p {
			padding: 10px 15px;
			margin-top: 0px;
			margin-bottom: 15px;
			background-color: #f9fbf7;
			border-radius: 4px;
			justify-content: space-between;
		}

		.octicon-x {
			cursor: pointer;
		}
	}
</style>
