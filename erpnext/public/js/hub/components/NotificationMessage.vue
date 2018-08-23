<template>
	<div class="subpage-message">
        <p class="text-muted flex">
            <span v-html="message"></span>
            <i class="octicon octicon-x text-extra-muted"></i>
        </p>
    </div>
</template>

<script>

export default {
	name: ' notification-message',
	props: {
		message: String,
	}
}
</script>

<style scoped></style>
