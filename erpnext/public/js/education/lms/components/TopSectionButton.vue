<template>
    <button v-if="isLoggedIn" class='btn btn-primary btn-lg' @click="primaryAction()">{{ buttonName }}</button>
	<a v-else class='btn btn-primary btn-lg' href="/login#signup">{{ buttonName }}</a>
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
        if(this.isLoggedIn && this.$route.name == 'program'){
                frappe.call({
                    method: "erpnext.www.lms.get_continue_data",
                    args: {
                        program_name: this.$route.params.program_name
                    }
                }).then( r => {
                    this.nextContent = r.message.content,
                    this.nextContentType = r.message.content_type,
                    this.nextCourse = r.message.course
                })
        }

        if(this.isLoggedIn){
            if(lms.store.checkProgramEnrollment(this.$route.params.program_name)){
            	if(this.$route.name == 'home'){
                    this.buttonName = 'Explore Courses'
            	}
                else if(this.$route.name == 'program'){
                    this.buttonName = 'Start Course'
                }
            }
            else {
                this.buttonName = 'Enroll Now'
            }
        }
        else{
            this.buttonName = 'Sign Up'
            }
    },
    methods: {
        primaryAction() {
            if(this.$route.name == 'home'){
                return
            }
            else if(this.$route.name == 'program' && lms.store.checkProgramEnrollment(this.$route.params.program_name)){
                this.$router.push({ name: 'content', params: { program_name: this.$route.params.program_name, course: this.nextCourse, type: this.nextContentType, content: this.nextContent}})
            }
            else {
                frappe.call({
                method: "erpnext.www.lms.enroll_in_program",
                args:{
                    program_name: this.$route.params.program_name,
                    student_email_id: frappe.session.user
                }
                })
                lms.store.updateEnrolledPrograms()
            }
        },
    }
};
</script>