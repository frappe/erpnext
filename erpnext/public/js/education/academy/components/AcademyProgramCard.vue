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
            <a v-if="this.$root.$data.isLogin" class='btn btn-secondary btn-sm' @click="primaryAction()">{{ buttonName }}</a>
            <a v-else class='btn btn-secondary btn-sm' href="/login#signup">Sign Up</a>
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
    methods: {
        primaryAction(){
            if(this.$root.$data.isLogin){
                if(this.$root.$data.checkProgramEnrollment(this.program_code)){
                    this.$router.push('/Program/' + program.name)
                }
                else {
                    this.enroll()
                }
            }
        },
        enroll() {
            frappe.call({
                method: "erpnext.www.academy.enroll_in_program",
                args:{
                    program_name: this.program_code,
                    student_email_id: frappe.session.user
                }
            })
            this.$root.$data.enrolledPrograms.add(this.program_code)
            this.$root.$data.updateEnrolledPrograms()
        }
    },
    computed: {
        buttonName() {
            if(this.$root.$data.isLogin){
                if(this.$root.$data.checkProgramEnrollment(this.program_code)){
                    return "Start Course"
                }
                else {
                    return "Enroll"
                }
            }
        }
    }
};
</script>

<style lang="css" scoped>
    a {
    text-decoration: none;
}
</style>