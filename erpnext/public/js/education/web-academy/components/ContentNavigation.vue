<template>
	<div class="nav-buttons">
		<button class='btn btn-outline-secondary' @click="$router.go(-1)">Back</button>
		<button v-if="nextContent" class='btn btn-primary' @click="$router.push({ name: 'content', params: { course: $route.params.course, type:nextContentType, content:nextContent }})">Next</button>
		<button v-else class='btn btn-primary' @click="$router.push({ name: 'program', params: { code: $route.params.code}})">Finish Course</button>
	</div>
</template>

<script>
export default {
	props: ['nextContent', 'nextContentType'],
	name: 'ContentNavigation'
};
</script>

<style lang="css" scoped>
	.nav-buttons {
		position: absolute;
  		bottom: 0;
  		right: 0;
	}
</style>
