<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Course Content
                    <ul class="mb-0 mt-1">
                        <li v-for="content in course.course_content" :key="content.name">
                            <router-link v-if="isLogin" tag="a" :class="'text-muted'" :to="{name: 'content', params:{program_name: program_name, course: course.name, type:content.content_type, content: content.content} }">
                                <span style="padding-right: 0.4em"><i :class="iconClass(content.content_type)"></i></span>{{ content.content }}
                            </router-link>
                            <div v-else><span style="padding-right: 0.4em"><i :class="iconClass(content.content_type)"></i></span>{{ content.content }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button
                    :type="buttonType"
                    size="sm btn-block"
                    :route="firstContentRoute"
                >
                    {{ courseMeta.flag }}
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
            isLogin: lms.store.isLogin,
            courseMeta: {}
        }
    },
    mounted() {
        if(this.isLogin) this.getCourseMeta().then(data => this.courseMeta = data)
    },
    components: {
        AButton
    },
    computed: {
        firstContentRoute() {
            return `${this.program_name}/${this.course.name}/${this.courseMeta.content_type}/${this.courseMeta.content}`
        },
        buttonType() {
            if (this.courseMeta.flag == "Start Course" ){
                return "primary"
            }
            else if (this.courseMeta.flag == "Complete" ) {
                return "success"
            }
            else if (this.courseMeta.flag == "Continue" ) {
                return "info"
            }
            else {
                return " hidden"
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
					course_name: this.course.name
				})
		}
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
    }
    .fa {
        font-size: 0.8em;
    }
</style>