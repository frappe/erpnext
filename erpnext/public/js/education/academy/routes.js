import AcademyHome from "./academy/pages/AcademyHome.vue";
import AcademyProgramPage from "./academy/pages/AcademyProgramPage.vue";
import AcademyCoursePage from "./academy/pages/AcademyCoursePage.vue";

const routes = [
	{name: 'home', path: '', component: AcademyHome},
	{name: 'program', path: '/Program/:program_name', component: AcademyProgramPage, props: true},
	{name: 'content', path: '/Program/:code/:course/:type/:content', component: AcademyCoursePage, props: true},
];

export default routes;