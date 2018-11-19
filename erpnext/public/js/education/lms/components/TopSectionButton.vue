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
                this.getContinueData().then( data => {
                    this.nextContent = data.content,
                    this.nextContentType = data.content_type,
                    this.nextCourse = data.course
                })
        }
        this.computeButtons()
    },
    methods: {
        computeButtons(){
            if(this.isLoggedIn){
                if(lms.store.enrolledPrograms.has(this.$route.params.program_name)){
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
        getContinueData() {
            lms.call({
                    method: "get_continue_data",
                    args: {
                        program_name: this.$route.params.program_name
                    }
                })
        },
        primaryAction() {
            if(this.$route.name == 'home'){
                return
            }
            else if(this.$route.name == 'program' && lms.store.enrolledPrograms.has(this.$route.params.program_name)){
                this.$router.push({ name: 'content', params: { program_name: this.$route.params.program_name, course: this.nextCourse, type: this.nextContentType, content: this.nextContent}})
            }
            else {
                lms.call({
                method: "enroll_in_program",
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