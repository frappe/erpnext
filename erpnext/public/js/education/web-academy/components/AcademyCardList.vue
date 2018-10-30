<template>
	<section class='section-padding section-bg'>
	<div class='container'>
		<h3 class='text-center'>Featured Programs</h3>
		<p class='lead text-center'>Master Engineering</p>
		<AcademyProgramCard v-for="program in featured_programs" v-bind:id="program" v-bind:title="program"/>
		<div class='mt-4 text-center'>
			<a class="btn btn-primary btn-lg" href="/program">View All</a>
		</div>
	</div>
</section>
</template>
<script>
import AcademyProgramCard from "../components/AcademyProgramCard.vue"
export default {
    name: "AcademyCardList",
    data() {
    	return {
    		featured_programs: [],
    	};
    },
    mounted() {
    	frappe.call("erpnext.www.academy.get_featured_programs").then(r => {
    		this.featured_programs = r.message
    	})
    },
    components: {
    	AcademyProgramCard
    }
};
</script>