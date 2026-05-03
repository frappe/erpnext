<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import QueueDrawer from '../components/QueueDrawer.vue';
import RepairHistoryDrawer from '../components/RepairHistoryDrawer.vue';
import QualityObservationRecorder from '../components/QualityObservationRecorder.vue';

const work_context = reactive({
    role: "Quality Analyst",
    assigned_line: "",
    assigned_station: "Quality Check",
    assigned_shift: "",
    job_card: "ABC-123-345",
});

const fetchWorkContext = async () => {
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.attendance_shift;
    }
};

const jobCardNumber = ref(null);
const slabSize = ref(null);
const selectedSlab = ref(null);
const slabQAReport = ref(null);
const mixerNumber = ref(null);
const isQAStarted = ref(false);
const hourglassRotation = ref(0);
const hourglassIcon = ref('fa-hourglass-3');
let hourglassInterval = null;
const isProcessing = ref(false);
const showRepairHistoryModal = ref(false);
const showQueueDrawer = ref(false);
const colourOptions = ref([]);
const queueSlabs = ref([]);
const originalRepairType = ref('');

// Visual Observation State
const observations = ref([]);

const fetchQueueSlabs = async () => {
    const res = await frappe.call({
        method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_slab_queue',
        args: {
            line: work_context.assigned_line,
            slab_to_exclude: selectedSlab.value?.name
        }
    });

	if (res.message) {
		queueSlabs.value = res.message;
    }
};

const productionDate = computed(() => {
    if (!selectedSlab.value?.creation) return "";

    const dateStr = selectedSlab.value.creation.split(' ')[0];
    const [year, month, day] = dateStr.split('-');

    const months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    return `${day} ${months[parseInt(month) - 1]} ${year}`;
});

const target_slab_thickness = computed(() => {
    if (!selectedSlab.value?.template) return "";
    return selectedSlab.value.template.split('-')[2].trim();
});

const form = reactive({
    // Basic Details (Auto-filled)
    name: '',
    date: '',
    shift: '',
    job_card: '',
    // Slab Details (Auto-filled)
    slab: '',
    slab_template: '',
    // Slab Dimensions
    slab_length: null,
    slab_width: null,
    slab_thickness: null,
    // Quality Measurements
    filler_spot: '',
    contamination: '',
    shade: '',
    // Paper Deep
    paper_deep_front: '',
    paper_deep_back: '',
    // Crack
    crack_front: '',
    crack_back: '',
    // Grading & Remarks
    bend: null,
    repair: '',
    recovery_type: [],
    repolish_type: [],
    recalibration_type: [],
    grade: '',
    use_for_samples: 0,
    remarks: '',
});

const grades = ref([]);
const repairOptions = ref([]);
const recoveryOptions = ref([]);
const repolishOptions = ref([]);
const recalibrationOptions = ref([]);
const shadeOptions = ref([]);
const observationColour = ref('');

const fetchGrades = async () => {
	const list = await frappe.db.get_list('Slab Quality Grade', {
		fields: ['name', 'code', 'color'],
		order_by: 'code asc',
	});

	if (list && list.length) {
		grades.value = list;
    }
};

const fetchRepairOptions = async () => {
    const r = await frappe.call({
		method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_repair_options',
    });

    if (r.message && typeof r.message === 'object') {
        repairOptions.value = r.message.repair || [];
        recoveryOptions.value = r.message.recovery_type || [];
        repolishOptions.value = r.message.repolish_type || [];
        recalibrationOptions.value = r.message.recalibration_type || [];
		shadeOptions.value = r.message.shade || [];
		colourOptions.value = r.message.colour || [];
		observationColour.value = observationColour.value || r.message.colour[0] || "red";
    }
};

const fetchExistingQCReport = async (qc_name) => {
	if (!qc_name) {
		slabQAReport.value = null;
		observationColour.value = colourOptions?.value ? colourOptions.value[0] : "red";
		originalRepairType.value = null;
		return;
    };

    const res = await frappe.call({
        method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_slab_qc_report',
        args: {
            qc_name: qc_name
        }
    });

	if (res.message) {
		slabQAReport.value = res.message;
		observationColour.value = res.message.colour;
		originalRepairType.value = res.message.repair;
        const report = res.message;
        Object.assign(form, {
	        name: report.name,
            date: report.date,
            shift: report.shift,
            job_card: report.job_card,
            slab: report.slab,
            slab_template: report.slab_template,
            slab_length: report.slab_length,
            slab_width: report.slab_width,
            slab_thickness: report.slab_thickness,
            filler_spot: report.filler_spot,
            contamination: report.contamination,
            shade: report.shade,
            paper_deep_front: report.paper_deep_front,
            paper_deep_back: report.paper_deep_back,
            crack_front: report.crack_front,
            crack_back: report.crack_back,
            bend: report.bend,
            repair: '', // Initialize as an empty value so that the operator can select the actual type after analysis.
            recovery_type: (report.recovery_type || []).map(d => d.recovery_reason),
            repolish_type: (report.repolish_type || []).map(d => d.repolish_reason),
            recalibration_type: (report.recalibration_type || []).map(d => d.recalibration_reason),
            grade: report.grade,
            use_for_samples: report.use_for_samples || 0,
			remarks: report.remarks,
        });

		if (report.observations && report.observations.length) {
			observations.value = report.observations.map(obs => ({
				name: obs.name,
				x: obs.x,
				y: obs.y,
				text: obs.text,
                colour: obs.colour,
            }));
        }
    }
};

const get_slab_for_qa = async (job_card_number, slab_number = null, exclude_job_card = null, play_ding = false) => {
    const res = await frappe.call({
        method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_slab_or_jobcard_for_qa',
        args: {
            line: work_context.assigned_line,
			job_card_number: job_card_number,
			slab_number: slab_number,
			exclude_job_card: exclude_job_card,
        }
    });

	if (res.message) {
        if (play_ding && res.message.slab && (!selectedSlab.value || selectedSlab.value.name !== res.message.slab.name)) {
            erpnext.utils.play_ding("new_slab");
        }

        jobCardNumber.value = res.message.job_card?.name || jobCardNumber.value;
        slabSize.value = res.message.slab_size;
        mixerNumber.value = res.message.job_card?.mixer_number || res.message.slab?.child_line;
        await selectSlab(res.message.slab);
        isQAStarted.value = res.message.job_card?.status === "Work In Progress";
    }
}


const selectSlabFromQueue = async (slab) => {
	await get_slab_for_qa(null, slab?.name, jobCardNumber.value);
	showQueueDrawer.value = false;
};


async function selectSlab(slab) {
    if (!slab) {
        selectedSlab.value = null;
        jobCardNumber.value = null;
        isQAStarted.value = false;
        return;
    }

    selectedSlab.value = slab;
    isQAStarted.value = false;
    // Reset and Auto-fill form
    Object.assign(form, {
        name: '',
        date: frappe.datetime.nowdate(),
        shift: work_context.assigned_shift,
        job_card: jobCardNumber.value,
        slab: slab.name,
        slab_template: slab.template,
        slab_length: null,
        slab_width: null,
        slab_thickness: null,
        filler_spot: null,
        contamination: null,
        shade: '',
        paper_deep_front: null,
        paper_deep_back: null,
        crack_front: null,
        crack_back: null,
        bend: null,
        repair: '',
        recovery_type: [],
        repolish_type: [],
        recalibration_type: [],
        grade: '',
        use_for_samples: 0,
        remarks: '',
    });

    // Clear observations
    observations.value = [];

    await fetchExistingQCReport(slab.quality_assessment);
}

function handleRepairChange() {
    form.recovery_type = [];
    form.repolish_type = [];
    form.recalibration_type = [];
    form.grade = '';
    form.use_for_samples = 0;
}

const confirmAndTag = async () => {
    if (!selectedSlab.value) {
        return;
    }

    if (!form.slab_length || !form.slab_width || !form.slab_thickness) {
        frappe.msgprint(__('Please fill in all required fields (Length, Width, Thickness)'));
        return;
    }

    if (!form.repair) {
        frappe.msgprint(__('Please select a Repair type'));
        return;
    }

    if (form.repair === 'None' && !form.grade) {
        frappe.msgprint(__('Please select Grade since Repair is None'));
        return;
    }

    if (form.repair === 'Recovery' && !form.recovery_type.length) {
        frappe.msgprint(__('Please select Recovery Type'));
        return;
    }

    if (form.repair === 'Repolish' && !form.repolish_type.length) {
        frappe.msgprint(__('Please select Repolish Type'));
        return;
    }

    if (form.repair === 'Recalibration' && !form.recalibration_type.length) {
        frappe.msgprint(__('Please select Recalibration Type'));
        return;
    }

    frappe.confirm(
        __('Are you sure you want to submit this quality report?'),
        async () => {
            try {
                isProcessing.value = true;
                const report_data = { ...form };
                report_data.observations = observations.value;
                report_data.recovery_type = form.recovery_type.map(r => ({ recovery_reason: r }));
                report_data.repolish_type = form.repolish_type.map(r => ({ repolish_reason: r }));
                report_data.recalibration_type = form.recalibration_type.map(r => ({ recalibration_reason: r }));

                const res = await frappe.call({
                    method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.submit_qa_report',
                    args: {
                        report: report_data,
                        shift: work_context.assigned_shift,
                        job_card: jobCardNumber.value,
						slab_number: selectedSlab.value.name,
                    },
                    freeze: true
                });

                if (res && res.message) {
                    frappe.show_alert(
                        __(`Quality Report submitted and Slab ${selectedSlab.value.name} checked out.`)
                    );

                    erpnext.utils.play_ding("submit");

                    jobCardNumber.value = null;
                    selectedSlab.value = null;
                    get_slab_for_qa(null, null, null, true);
                }
            } catch (e) {
                console.error(e);
                frappe.msgprint(__('An error occurred while submitting the quality report.'));
            } finally {
                isProcessing.value = false;
            }
        }
    );
};

const raiseQualityAlarm = async () => {
    if (!selectedSlab.value) return;

    // await frappe.call({
    //     method: 'your_app.api.raise_quality_alarm',
    //     args: {
    //         source: 'Quality Analyst Station',
    //         slab_name: selectedSlab.value.name,
    //     },
    // });
    frappe.show_alert(__('Quality alarm raised for {0}', [selectedSlab.value.name]));
};

onMounted(async () => {
    const route = frappe.get_route();
    jobCardNumber.value = route[1] || null;

    await fetchWorkContext();
    await loadData();

    document.addEventListener("refresh-qa-station", () => {
        loadData();
    });

    startHourglassAnimation();
});

async function loadData() {
    await get_slab_for_qa(jobCardNumber.value);
    await fetchGrades();
    await fetchRepairOptions();
    await fetchQueueSlabs();
}

onUnmounted(() => {
    if (hourglassInterval) clearInterval(hourglassInterval);
});

function startHourglassAnimation() {
    hourglassInterval = setInterval(() => {
        hourglassRotation.value += 180;
        setTimeout(() => {
            hourglassIcon.value = hourglassIcon.value === 'fa-hourglass-3' ? 'fa-hourglass-1' : 'fa-hourglass-3';
        }, 500);
    }, 1000);
}


frappe.realtime.on('slab_checkout', (slab) => {
    // If the slab has been checked out on a different line or the checked out slab is not in 'Polishing', then ignore the event.
    if (slab.line !== work_context.assigned_line || slab.status !== 'Polishing' || !slab.is_cur_stage_complete) return;

    if (!selectedSlab.value) {
        get_slab_for_qa(null, null, null, true);
    }

    // TODO: Use this if a queue is intelligently implemented on the frontend.
    // if (!selectedSlab.value) {
    //     jobCardNumber.value = null;
    //     selectSlab(slab);
    // }
});

const startProcess = async () => {
    if (!selectedSlab.value) return;

    isProcessing.value = true;
    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.start_qa_process',
			args: {
            	line: work_context.assigned_line,
				slab_number: selectedSlab.value.name,
                job_card_number: jobCardNumber.value,
            }
        });

        jobCardNumber.value = res.message;
        isQAStarted.value = true;
    } catch (e) {
        console.error('Failed to start job card', e);
    } finally {
        isProcessing.value = false;
    }
};

const showQueue = async () => {
	showQueueDrawer.value = true;
	fetchQueueSlabs();
};
</script>

<template>
    <div class="page-card d-flex">
        <div class="flex-fill pl-4">
            <Transition name="pop-switch" mode="out-in">
                <main class="main-container" v-if="selectedSlab" key="qa-main">
                    <div class="slab-info-card p-4 border rounded mb-4 d-flex align-items-center">
                        <div class="slab-thumbnail-large mr-4"></div>
                        <div class="slab-main-info">
                            <div class="slab-id h3 font-weight-bold mb-1">{{ selectedSlab.name }}</div>
                            <div class="slab-template text-muted" style="font-size: 1.1rem;">
                                {{ selectedSlab.template }}
                            </div>
                            <span v-if="mixerNumber">Mixer: {{ mixerNumber }}</span><span class="text-danger" v-if="originalRepairType"> ({{ originalRepairType }})</span>
                        </div>
                        <div class="flex-fill"></div>
                        <div class="slab-meta-boxes d-flex">
                            <div v-if="slabQAReport?.recovery_count > 0" class="meta-box mr-4 p-3 rounded cursor-pointer" @click="showRepairHistoryModal = true">
                                <div class="meta-label text-danger small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-refresh mr-2"></span>{{ __('Recoveries') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold text-danger">
                                    {{ slabQAReport.recovery_count }}
                                </div>
                            </div>
                            <div v-if="slabQAReport?.repolish_count > 0" class="meta-box mr-4 p-3 rounded cursor-pointer" @click="showRepairHistoryModal = true">
                                <div class="meta-label text-danger small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-paint-brush mr-2"></span>{{ __('Repolishes') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold text-danger">
                                    {{ slabQAReport.repolish_count }}
                                </div>
                            </div>
                            <div v-if="slabQAReport?.recalibration_count > 0" class="meta-box mr-4 p-3 rounded cursor-pointer" @click="showRepairHistoryModal = true">
                                <div class="meta-label text-danger small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-cogs mr-2"></span>{{ __('Recalibrations') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold text-danger">
                                    {{ slabQAReport.recalibration_count }}
                                </div>
                            </div>
                            <div class="meta-box mr-4 p-3 rounded">
                                <div class="meta-label text-muted small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-calendar-o mr-2"></span>{{ __('Production Date') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold">
                                    {{ productionDate }}
                                </div>
                            </div>
                            <div class="meta-box p-3 rounded">
                                <div class="meta-label text-muted small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-arrows-v mr-2"></span>{{ __('Target Thickness') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold">
                                    {{ target_slab_thickness }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-if="!isQAStarted" class="d-flex flex-column align-items-center justify-content-center p-5 border rounded"
                        style="min-height: 400px; background: var(--card-bg);">
                        <button class="btn btn-primary btn-lg px-5 font-weight-bold mb-4"
                            style="font-size: 1.2rem; transform: scale(1.2);" :disabled="isProcessing" @click="startProcess()">
                            <span v-if="isProcessing" class="fa fa-spinner fa-spin mr-2"></span>
                            <span v-else class="fa fa-play mr-2"></span>{{ __('Start Quality Analysis') }}
                        </button>
                        <button v-if="queueSlabs.length" class="btn btn-primary btn-md px-5 font-weight-bold mt-3" @click="showQueue();">
                            <span class="fa fa-list mr-2"></span>{{ __('Show Slab Queue') }}
                        </button>
                    </div>

                    <div v-else class="qa-form-section p-4 border rounded">
                        <!-- Slab Dimensions -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Slab Dimensions') }}</h5>
                        <div class="row mb-4">
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Length (mm)') }}</label>
                                <input type="number" v-model="form.slab_length" class="form-control" required>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Width (mm)') }}</label>
                                <input type="number" v-model="form.slab_width" class="form-control" required>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Thickness (mm)') }}</label>
                                <input type="number" v-model="form.slab_thickness" class="form-control" required>
                            </div>
                        </div>

                        <!-- Quality Measurements -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Quality Measurements') }}</h5>
                        <div class="row mb-4">
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Filler Spot') }}</label>
                                <input type="text" v-model="form.filler_spot" class="form-control">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Contamination') }}</label>
                                <input type="text" v-model="form.contamination" class="form-control">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Shade') }}</label>
                                <select v-model="form.shade" class="form-control">
                                    <option value="">{{ __('Select Shade') }}</option>
                                    <option v-for="option in shadeOptions" :key="option" :value="option">
                                        {{ __(option) }}
                                    </option>
                                </select>
                            </div>
                        </div>

                        <!-- Paper Deep & Crack -->
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <h5 class="mb-4 border-bottom pb-2">{{ __('Paper Deep') }}</h5>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Front') }}</label>
                                        <input type="text" v-model="form.paper_deep_front" class="form-control">
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Back') }}</label>
                                        <input type="text" v-model="form.paper_deep_back" class="form-control">
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5 class="mb-4 border-bottom pb-2">{{ __('Crack') }}</h5>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Front') }}</label>
                                        <input type="text" v-model="form.crack_front" class="form-control">
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Back') }}</label>
                                        <input type="text" v-model="form.crack_back" class="form-control">
                                    </div>
                                </div>
                            </div>
                        </div>

                        <h5 class="mb-4 border-bottom pb-2">{{ __('Observations') }}</h5>
                        <QualityObservationRecorder 
                            v-model:observations="observations" 
                            :slabSize="slabSize" 
                            :observationColour="observationColour" 
                        />

                        <!-- Grading & Remarks -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Grading & Remarks') }}</h5>
                        <div class="row">
                            <div class="col-md-3 mb-3">
                                <label class="small text-muted">{{ __('Bend (mm)') }}</label>
                                <input type="number" v-model="form.bend" class="form-control">
                            </div>
                            <div class="col-md-3 mb-3">
                                <label class="small text-muted">{{ __('Repair') }}<span class="text-danger">*</span></label>
                                <select v-model="form.repair" class="form-control" required @change="handleRepairChange">
                                    <option value="">{{ __('Select Repair') }}</option>
                                    <option v-for="option in repairOptions" :key="option" :value="option">
                                        {{ __(option) }}
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-3 mb-3" v-if="form.repair === 'None'">
                                <label class="small text-muted">{{ __('Grade') }}<span class="text-danger">*</span></label>
                                <select v-model="form.grade" class="form-control" :required="form.repair === 'None'">
                                    <option value="">{{ __('Select Grade') }}</option>
                                    <option v-for="g in grades" :key="g.code" :value="g.code">
                                        {{ g.code }}
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-3 mb-3 d-flex align-items-center pt-4" v-if="form.repair === 'None' && form.grade?.toLowerCase().includes('reject')">
                                <div class="form-check">
                                    <input type="checkbox" v-model="form.use_for_samples" :true-value="1" :false-value="0" id="use_for_samples" class="form-check-input">
                                    <label class="form-check-label font-weight-bold" for="use_for_samples">
                                        {{ __('Use for samples') }}
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3" v-if="form.repair === 'Recovery'">
                                <label class="small text-muted">{{ __('Recovery Type') }}<span class="text-danger">*</span></label>
                                <div class="border rounded p-2" style="overflow-y: auto;">
                                    <div v-for="option in recoveryOptions" :key="option" class="form-check small mb-1">
                                        <input type="checkbox" :id="'recov-' + option" :value="option" v-model="form.recovery_type" class="form-check-input">
                                        <label class="form-check-label" :for="'recov-' + option">{{ __(option) }}</label>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3" v-if="form.repair === 'Repolish'">
                                <label class="small text-muted">{{ __('Repolish Type') }}<span class="text-danger">*</span></label>
                                <div class="border rounded p-2" style="overflow-y: auto;">
                                    <div v-for="option in repolishOptions" :key="option" class="form-check small mb-1">
                                        <input type="checkbox" :id="'repol-' + option" :value="option" v-model="form.repolish_type" class="form-check-input">
                                        <label class="form-check-label" :for="'repol-' + option">{{ __(option) }}</label>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3" v-if="form.repair === 'Recalibration'">
                                <label class="small text-muted">{{ __('Recalibration Type') }}<span class="text-danger">*</span></label>
                                <div class="border rounded p-2" style="overflow-y: auto;">
                                    <div v-for="option in recalibrationOptions" :key="option" class="form-check small mb-1">
                                        <input type="checkbox" :id="'recal-' + option" :value="option" v-model="form.recalibration_type" class="form-check-input">
                                        <label class="form-check-label" :for="'recal-' + option">{{ __(option) }}</label>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3">
                                <label class="small text-muted">{{ __('Remarks') }}</label>
                                <textarea v-model="form.remarks" class="form-control" rows="1"></textarea>
                            </div>
                        </div>

                        <div class="mt-4 border-top pt-4 d-flex justify-content-end align-items-center">
                            <div class="actions">
                                <button class="btn btn-primary btn-lg px-5" :disabled="isProcessing" @click="confirmAndTag">
                                    <span v-if="isProcessing" class="fa fa-spinner fa-spin mr-2"></span>
                                    <span v-else class="fa fa-check mr-2"></span>{{ __('Submit Quality Report') }}
                                </button>
                                <!-- <button class="btn btn-outline-danger btn-lg ml-2" @click="raiseQualityAlarm">
                                    <span class="fa fa-bell mr-2"></span>{{ __('Raise Alarm') }}
                                </button> -->
                            </div>
                        </div>
                    </div>
                </main>
                <div v-else key="no-slab-message" class="no-slab-message text-center p-5 text-muted"
                    style="border: 2px dashed; border-radius: 8px;">
                    <div class="mb-3">
                        <span :class="['fa', hourglassIcon]"
                            :style="{ transform: `rotate(${hourglassRotation}deg)`, transition: 'transform 0.5s', display: 'inline-block' }"
                            style="font-size: 2rem;">
                        </span>
                    </div>
                    <!-- <h5>{{ __('Select a slab from the list to start quality analysis') }}</h5> -->
                    <h3>{{ __('There are no slabs available for quality analysis right now.') }}</h3>
                    <h3>{{ __('Please wait for the next slab to arrive.') }}</h3>
                </div>
            </Transition>
        </div>

        <!-- Queue Drawer Component -->
        <QueueDrawer 
            v-model:show="showQueueDrawer" 
            :queueSlabs="queueSlabs" 
            :isQAStarted="isQAStarted"
            @select="selectSlabFromQueue" 
            @fetch-queue="fetchQueueSlabs"
        />

        <!-- Repair History Drawer Component -->
        <RepairHistoryDrawer 
            v-model:show="showRepairHistoryModal" 
            :slabQAReport="slabQAReport" 
        />
    </div>
</template>

<style scoped>
.page-card {
    min-height: 80vh;
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.incoming-list {
    width: 100%;
}

.incoming-item {
    cursor: pointer;
    background-color: var(--fg-color, #f8f9fa);
    border-color: var(--border-color) !important;
    transition: all 0.2s ease;
}

.incoming-item:hover {
    border-color: var(--primary-color) !important;
}

.incoming-item.selected {
    background-color: var(--control-bg-on-gray, #e2edff);
    border-color: var(--primary-color) !important;
}

.empty-state {
	background-color: var(--fg-color, #f8f9fa);
    border: 1px solid var(--border-color) !important;
}

.slab-container {
    display: flex;
    width: 100%;
    align-items: center;
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: #1f2937;
}

.slab-thumbnail-large {
    width: 64px;
    height: 64px;
    border-radius: 8px;
    background: #1e3a5f;
    flex-shrink: 0;
}

.cursor-pointer {
    cursor: pointer;
}

.meta-box {
    background-color: var(--fg-color, #f8f9fa);
    min-width: 180px;
}

.meta-label {
    letter-spacing: 0.05em;
    font-weight: 500;
}

.header {
    display: flex;
    justify-content: space-between;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.operator-info {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.operator-time {
    font-size: 1.5rem;
    font-weight: bold;
}

.breadcrumb {
    font-size: 0.8rem;
    color: var(--text-muted);
}

.breadcrumb span+span::before {
    content: ' / ';
}

.slab-info-card,
.qa-form-section {
    background: var(--card-bg, #fff);
}

.grade-a {
    color: #28a745;
}

.grade-b {
    color: #17a2b8;
}

.grade-c {
    color: #ffc107;
}

.grade-d {
    color: #dc3545;
}

.list-enter-active,
.list-leave-active {
    transition: all 0.2s ease-out;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateY(30px);
}

.pop-switch-enter-active {
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pop-switch-leave-active {
    transition: all 0.2s ease-in;
}

.pop-switch-enter-from,
.pop-switch-leave-to {
    opacity: 0;
    transform: scale(0.9);
}
</style>

