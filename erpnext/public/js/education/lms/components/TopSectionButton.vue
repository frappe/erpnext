<template>
    <button v-if="isLoggedIn" class='btn btn-primary btn-md' @click="primaryAction()">{{ buttonName }}</button>
	<a v-else class='btn btn-primary btn-md' href="/login#signup">{{ buttonName }}</a>
</template>
<script>
export default {
    name: "TopSectionButton",
    data() {
        return {
            buttonName: '',
            isLoggedIn: lms.store.checkLogin(),
            nextContent: '',
            nextContentType: '',
            nextCourse: '',
            link: '',
        }
    },
    mounted() {
        this.computeButtons()
    },
    methods: {
        computeButtons(){
            if(this.isLoggedIn){
                    this.buttonName = 'Explore Programs'
            }
            else{
                this.buttonName = 'Sign Up'
            }
        },
        primaryAction() {
            if(this.$route.name == 'home'){
                this.$router.push('List/Program');
            }
            else if(this.$route.name == 'program' && lms.store.enrolledPrograms.includes(this.$route.params.program_name)){
                this.$router.push({ name: 'content', params: { program_name: this.$route.params.program_name, course: this.nextCourse, type: this.nextContentType, content: this.nextContent}})
            }
            else {
                lms.call("enroll_in_program",
                    {
                        program_name: this.$route.params.program_name,
                        student_email_id: frappe.session.user
                    }
                )
                lms.store.updateEnrolledPrograms()
            }
        },
    }
};
</script>