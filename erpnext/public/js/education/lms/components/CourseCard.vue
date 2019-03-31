<template>
    <div class="mt-3 col-md-4 col-sm-12">
        <div class="card h-100">
            <div class="card-hero-img" v-if="course.hero_image" v-bind:style="{ 'background-image': 'url(' + image + ')' }"></div>
            <div v-else class="card-image-wrapper">
                <div class="image-body">{{ course.course_name }}</div>
            </div>
            <div class='card-body'>
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
            <div class='text-right p-3'>
                <div class='course-buttons text-center'>
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
    .course-buttons {
        margin-bottom: 1em;
    }

    div.card-hero-img {
        height: 220px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-color: rgb(250, 251, 252);
    }

    .card-image-wrapper {
        display: flex;
        overflow: hidden;
        height: 220px;
        background-color: rgb(250, 251, 252);
    }

    .image-body {
        align-self: center;
        color: #d1d8dd;
        font-size: 24px;
        font-weight: 600;
        line-height: 1;
        padding: 20px;
    }
</style>