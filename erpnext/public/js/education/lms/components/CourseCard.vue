<template>
    <div class="py-3 col-md-4 col-sm-12">
        <div class="card h-100">
            <div class="card-hero-img" v-if="course.hero_image" v-bind:style="{ 'background-image': 'url(' + image + ')' }"></div>
            <div v-else class="card-image-wrapper">
                <div class="image-body">{{ course.course_name }}</div>
            </div>
            <div class='card-body'>
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    {{ course.course_intro.substring(0,120) }}
                </span>
            </div>
            <div class='p-3' style="display: flex; justify-content: space-between;">
                <div>
                    <span v-if="complete"><i class="mr-2 text-success fa fa-check-circle" aria-hidden="true"></i>Course Complete</span>
                </div>
                <div class='text-right'>
                    <a-button
                        :type="'primary'"
                        size="sm"
                        :route="courseRoute"
                    >
                        {{ buttonName }}
                    </a-button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import AButton from './Button.vue';

export default {
    props: ['course', 'program_name'],
    name: "CourseCard",
    components: {
        AButton
    },
    data() {
        return {
            courseDetails: {},
        }
    },
    mounted() {
        if(lms.store.checkLogin()) this.getCourseDetails().then(data => this.courseDetails = data)
    },
    computed: {
        courseRoute() {
            return `${this.program_name}/${this.course.name}`
        },
        complete() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                if (this.courseDetails.flag === "Completed" ) {
                    return true
                }
                else {
                    return false
                }
            }
            else {
                return false
            }
        },
        isLogin() {
            return lms.store.checkLogin()
        },
        buttonName() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                return "Start Course"
            }
            else {
                return "Explore"
            }
        }
    },
    methods: {
        getCourseDetails() {
			return lms.call('get_student_course_details', {
                    course_name: this.course.name,
                    program_name: this.program_name
				})
        },
    }
};
</script>