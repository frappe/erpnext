
<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Topics
                    <ul class="mb-0 mt-1">
                        <li v-for="topic in course.course_topic" :key="topic.name">
                            <router-link v-if="isLogin" tag="a" :class="'text-muted'" :to="{name: 'course', params:{program_name: program_name, topic:topic.topic, course: course.name} }">
                                <span style="padding-right: 0.4em"></span>{{ topic.topic_name }}
                            </router-link>
                            <div v-else><span style="padding-right: 0.4em"></span>{{ topic.topic_name }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button v-if="isLogin"
                    :type="buttonType"
                    size="sm btn-block"
                    :route="firstContentRoute"
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
    data() {
        return {
            courseMeta: {}
        }
    },
    mounted() {
        if(lms.store.checkLogin()) this.getCourseMeta().then(data => this.courseMeta = data)
    },
    components: {
        AButton
    },
    computed: {
        firstContentRoute() {
            if(lms.store.checkLogin()){
                return `${this.program_name}/${this.course.name}/${this.courseMeta.content_type}/${this.courseMeta.content}`
            }
            else {
                return {}
            }
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
                return " hidden"
            }
        },
        isLogin() {
            // return lms.store.checkProgramEnrollment(this.program_name)
            return true
        },
        buttonName() {
            if(lms.store.checkLogin()){
                return this.courseMeta.flag
            }
            else {
                return "Enroll"
            }
        }
    },
    methods: {
        iconClass(content_type) {
            if(content_type == 'Video') return 'fa fa-play'
            if(content_type == 'Article') return 'fa fa-file-text-o'
            if(content_type == 'Quiz') return 'fa fa-question-circle-o'
        },
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
    li {
        list-style-type: none;
        padding: 0;

    .fa {
        font-size: 0.8em;
    }
</style>