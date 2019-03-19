<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Topics
                    <ul class="mb-0 mt-1">
                        <li v-for="topic in course.topics" :key="topic.name">
                            <div><span style="padding-right: 0.4em"></span>{{ topic.topic_name }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button
                    :type="buttonType"
                    size="sm btn-block"
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
            courseMeta: {},
        }
    },
    mounted() {
        if(lms.store.checkLogin()) this.getCourseMeta().then(data => this.courseMeta = data)
    },
    computed: {
        courseRoute() {
            return `${this.program_name}/${this.course.name}`
        },
        buttonType() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                if (this.courseMeta.flag == "Start Course" ){
                return "primary"
                }
                else if (this.courseMeta.flag == "Completed" ) {
                    return "success"
                }
                else if (this.courseMeta.flag == "Continue" ) {
                    return "info"
                }
            }
            else {
                return "info"
            }
        },
        isLogin() {
            return lms.store.checkLogin()
        },
        buttonName() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                return this.courseMeta.flag
            }
            else {
                return "Explore"
            }
        }
    },
    methods: {
        getCourseMeta() {
			return lms.call('get_course_meta', {
                    course_name: this.course.name,
                    program_name: this.program_name
				})
        },
    }
};
</script>

<style scoped>
    @media only screen and (max-width: 576px) {
        .course-buttons {
            margin-top: 1em;
        }
    }
</style>