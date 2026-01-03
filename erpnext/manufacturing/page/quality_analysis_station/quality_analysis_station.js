frappe.pages['quality-analysis-station'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Quality Analysis Station',
		single_column: true
	});
const $main = $(wrapper).find('.layout-main-section');
    $main.empty().append('<div id="qa-vue-root"></div>');

    // 1) inject CSS once
    if (!document.getElementById('qa-vue-style')) {
        const style = document.createElement('style');
        style.id = 'qa-vue-style';
        style.innerHTML = `/* paste ALL <style> CSS from your HTML here, without <style> tags */`;
        document.head.appendChild(style);
    }

    // 2) load Vue (CDN) once
    if (!window.Vue) {
        const vueScript = document.createElement('script');
        vueScript.src = 'https://unpkg.com/vue@3/dist/vue.global.prod.js';
        vueScript.onload = () => init_vue_app();
        document.body.appendChild(vueScript);
    } else {
        init_vue_app();
    }

    function init_vue_app() {
        const { createApp, ref, reactive, computed, onMounted, onUnmounted } = Vue;

        createApp({
            setup() {
                const currentTime = ref('');
                const currentDate = ref('');

                const slab = reactive({
                    name: 'SLB-2024-8820',
                    color: 'Midnight Blue',
                    color_hex: '#1e3a5f',
                    production_date: '05 Dec 2025',
                    target_thickness: 20,
                });

                const form = reactive({
                    thickness: null,
                    length: null,
                    width: null,
                    gloss: null,
                    surfacePits: '',
                    colorConsistency: false,
                    flexuralStrength: null,
                });

                let clockInterval;

                const updateClock = () => {
                    const now = new Date();
                    currentTime.value = now.toLocaleTimeString('en-US', { hour12: false });
                    currentDate.value = now.toLocaleDateString('en-US', {
                        weekday: 'short',
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                    });
                };

                const filledParams = computed(() => {
                    let count = 0;
                    if (form.thickness) count++;
                    if (form.length) count++;
                    if (form.width) count++;
                    if (form.gloss) count++;
                    if (form.surfacePits) count++;
                    if (form.colorConsistency !== null) count++;
                    if (form.flexuralStrength) count++;
                    return count;
                });

                const canClassify = computed(() => filledParams.value >= 5);

                const calculatedGrade = computed(() => {
                    if (!canClassify.value) return '-';
                    let score = 0;
                    if (form.thickness >= 19.5 && form.thickness <= 20.5) score += 20;
                    if (form.gloss >= 45 && form.gloss <= 60) score += 20;
                    if (form.surfacePits === 'none') score += 20;
                    else if (form.surfacePits === 'minor') score += 10;
                    if (form.colorConsistency) score += 20;
                    if (form.flexuralStrength >= 40 && form.flexuralStrength <= 90) score += 20;

                    if (score >= 90) return 'A';
                    if (score >= 70) return 'B';
                    if (score >= 50) return 'C';
                    return 'D';
                });

                const calculatedBin = computed(() => {
                    const grade = calculatedGrade.value;
                    if (grade === 'A') return 'Premium Stock';
                    if (grade === 'B') return 'Standard Stock';
                    if (grade === 'C') return 'Secondary Market';
                    return 'Reject / Reprocess';
                });

                const confirmAndTag = async () => {
                    await frappe.call({
                        method: 'your_app.api.submit_quality_analysis',
                        args: {
                            slab_name: slab.name,
                            data: {
                                ...form,
                                grade: calculatedGrade.value,
                                bin: calculatedBin.value,
                            },
                        },
                    });
                    frappe.show_alert(
                        __(`Slab ${slab.name} tagged as Grade ${calculatedGrade.value} → ${calculatedBin.value}`)
                    );
                };

                const raiseQualityAlarm = async () => {
                    await frappe.call({
                        method: 'your_app.api.raise_quality_alarm',
                        args: {
                            source: 'Quality Analyst Station',
                            slab_name: slab.name,
                        },
                    });
                    frappe.show_alert(__('Quality alarm raised for {0}', [slab.name]));
                };

                onMounted(() => {
                    updateClock();
                    clockInterval = setInterval(updateClock, 1000);
                });

                onUnmounted(() => clearInterval(clockInterval));

                return {
                    currentTime,
                    currentDate,
                    slab,
                    form,
                    filledParams,
                    canClassify,
                    calculatedGrade,
                    calculatedBin,
                    confirmAndTag,
                    raiseQualityAlarm,
                };
            },
            template: `<!-- paste ONLY the <body> content of your HTML here, replacing outer <body> with <div> -->
            <div>
              <header class="header">
                <div>
                  <div class="breadcrumb">
                    <span>Shop Floor Control</span>
                    <span>Work Order Execution</span>
                    <span>Generic Operator Screen</span>
                  </div>
                  <h1 class="page-title">Quality Analyst Station</h1>
                </div>
                <div class="operator-info">
                  <div>
                    <div class="operator-label">Operator</div>
                    <div class="operator-name">Sarah Connor</div>
                    <div class="operator-date">📅 {{ currentDate }}</div>
                  </div>
                  <div class="operator-time">{{ currentTime }}</div>
                  <div class="operator-avatar">
                    <!-- svg omitted for brevity, keep same as your HTML -->
                  </div>
                </div>
              </header>
              <!-- keep your <main class="main-container"> ... entire rest of markup ... -->
            </div>
            `,
        }).mount('#qa-vue-root');
    }
};