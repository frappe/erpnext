<template>
    <div class='card-deck mt-5'>
    <div class="card">
        <img :src="program.hero_image" style='height: 150px; width: auto'>
        <div class='card-body'>
            <router-link :to="'/Program/' + program.name">
                <h5 class='card-title'>{{ program.program_name }}</h5>
            </router-link>
            <div v-html="program.description"></div>
        </div>
        <div class='card-footer text-right'>
            <!-- <a class='video-btn btn btn-secondary btn-sm' data-toggle="modal" data-src=" insert jinja stuff here " data-target="#myModal">Watch Intro</a>&nbsp;&nbsp; -->
            <a class='btn btn-secondary btn-sm' href="/enroll?course=user">Enroll Now</a>
        </div>
    </div>
</div>
</template>
<script>
export default {
    props: ['program_code'],
    name: "AcademyProgramCard",
    data() {
    	return {
    		program: ''
    	};
    },
    mounted() {
    	frappe.call({
            method: "erpnext.www.academy.get_program_details",
            args: {
                program_name: this.program_code
            }
        }).then(r => {
    		this.program = r.message
    	})
    },
};
</script>

<style lang="css" scoped>
    a {
    text-decoration: none;
}
</style>