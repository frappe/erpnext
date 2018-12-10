<template>
	<div id="lms-root">
		<navbar></navbar>
	<router-view :key="$route.fullPath"></router-view>
	</div>
</template>
<script>
import Navbar from "./components/Navbar.vue"
export default {
	name: "lmsRoot",
	components: {
		Navbar
	}
};
</script>
