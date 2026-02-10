<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';

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
const mixerNumber = ref(null);
const isQAStarted = ref(false);
const hourglassRotation = ref(0);
const hourglassIcon = ref('fa-hourglass-3');
let hourglassInterval = null;

// Visual Observation State
const observations = ref([]);
const newObservation = ref(null);
const hoverCoordinates = ref({ x: 0, y: 0, visible: false });
const slabScale = ref(1); // pixels per mm
const visualizerRef = ref(null);

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

const form = reactive({
    // Basic Details (Auto-filled)
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
    fs: '',
    con: '',
    // Paper Deep
    paper_deep_front: '',
    paper_deep_back: '',
    // Crack
    crack_front: '',
    crack_back: '',
    // Others
    bend: null,
    grade: '',
    remarks: ''
});

const grades = ref([]);

const fetchGrades = async () => {
    const r = await frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Mahi Granites Settings'
        }
    });
    if (r.message && r.message.grades) {
        grades.value = r.message.grades;
    }
};

const get_slab_for_qa = async (job_card_number, play_ding = false) => {
    const res = await frappe.call({
        method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_slab_or_jobcard_for_qa',
        args: {
            line: work_context.assigned_line,
            job_card_number: job_card_number,
        }
    });

    if (res.message) {
        if (play_ding && res.message.slab && (!selectedSlab.value || selectedSlab.value.name !== res.message.slab.name)) {
            erpnext.utils.play_ding("new_slab");
        }

        jobCardNumber.value = res.message.job_card?.name || jobCardNumber.value;
        slabSize.value = res.message.slab_size;
        mixerNumber.value = res.message.job_card?.mixer_number || null;
        selectSlab(res.message.slab);
        isQAStarted.value = res.message.job_card?.status === "Work In Progress";
    }
}


function selectSlab(slab) {
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
        date: frappe.datetime.nowdate(),
        shift: work_context.assigned_shift,
        job_card: jobCardNumber.value,
        slab: slab.name,
        slab_template: slab.template,
        slab_length: null,
        slab_width: null,
        slab_thickness: null,
        fs: null,
        con: null,
        paper_deep_front: null,
        paper_deep_back: null,
        crack_front: null,
        crack_back: null,
        bend: null,
        grade: '',
        remarks: ''
    });
    
    // Clear observations
    observations.value = [];
    newObservation.value = null;
}


const confirmAndTag = async () => {
    if (!selectedSlab.value) {
        return;
    }

    if (!form.slab_length || !form.slab_width || !form.slab_thickness || !form.grade) {
        frappe.msgprint(__('Please fill in all required fields (Length, Width, Thickness, Grade)'));
        return;
    }

    try {
        form.observations = observations.value;
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.submit_qa_report',
            args: {
                report: form,
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
            get_slab_for_qa(null, true);
        }
    } catch (e) {
        console.error(e);
        frappe.msgprint(__('An error occurred while submitting the quality report.'));
    }
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

    // TODO: 
    //  1. Get the slab from the job card if job card is present in the route.
    //  2. Else, get the currently active job card and its associated slab.
    //  2. If there is an active job card, pre-select its slab.

    await fetchWorkContext();
    get_slab_for_qa(jobCardNumber.value);
    fetchGrades();

    startHourglassAnimation();
});

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
        get_slab_for_qa(null, true);
    }

    // TODO: Use this if a queue is intelligently implemented on the frontend.
    // if (!selectedSlab.value) {
    //     jobCardNumber.value = null;
    //     selectSlab(slab);
    // }
});

const startProcess = async () => {
    if (!selectedSlab.value) return;

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.start_qa_process',
            args: {
                slab_number: selectedSlab.value.name,
            }
        });

        jobCardNumber.value = res.message;
        isQAStarted.value = true;
    } catch (e) {
        console.error('Failed to start job card', e);
    }
};

// Visualizer Logic
const getScale = () => {
    if (!visualizerRef.value || !slabSize.value) return 1;
    // Use getBoundingClientRect for precise sub-pixel rendering and zoom handling
    const rect = visualizerRef.value.getBoundingClientRect();
    return rect.width / slabSize.value.length;
};

const updateScale = () => {
    if (visualizerRef.value) {
        slabScale.value = getScale();
    }
};

// Mouse tracking
const handleMouseMove = (event) => {
    if (!visualizerRef.value) return;
    updateScale(); // Ensure scale is always current (handles zoom/resize)
    const rect = visualizerRef.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Convert to mm
    const mmX = Math.round(x / slabScale.value);
    const mmY = Math.round(y / slabScale.value);
    
    // Clamp to slab dimensions
    if (mmX >= 0 && mmX <= slabSize.value.length && mmY >= 0 && mmY <= slabSize.value.breadth) {
        hoverCoordinates.value = { x: mmX, y: mmY, visible: true, clientX: event.clientX, clientY: event.clientY };
    } else {
        hoverCoordinates.value.visible = false;
    }
};

const handleMouseLeave = () => {
    hoverCoordinates.value.visible = false;
};

// Click to add observation
const editingObservationIndex = ref(null);

const handleSlabClick = (event) => {
    if (!visualizerRef.value || newObservation.value) return; // Don't start new if one is open
    
    // Clear editing state if clicking elsewhere
    editingObservationIndex.value = null;
    
    const rect = visualizerRef.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const mmX = Math.round(x / slabScale.value);
    const mmY = Math.round(y / slabScale.value);
    
    newObservation.value = {
        x: mmX,
        y: mmY,
        text: ''
    };
    
    // Auto-focus input next tick
    setTimeout(() => {
        const input = document.getElementById('obs-input');
        if (input) input.focus();
    }, 100);
};

const editObservation = (index) => {
    editingObservationIndex.value = index;
    newObservation.value = { ...observations.value[index] };
    
    // Auto-focus input next tick
    setTimeout(() => {
        const input = document.getElementById('obs-input');
        if (input) input.focus();
    }, 100);
};

const deleteObservation = () => {
    if (editingObservationIndex.value !== null) {
        observations.value.splice(editingObservationIndex.value, 1);
    }
    newObservation.value = null;
    editingObservationIndex.value = null;
};

const saveObservation = () => {
    if (newObservation.value && newObservation.value.text.trim()) {
        if (editingObservationIndex.value !== null) {
             observations.value[editingObservationIndex.value] = { ...newObservation.value };
        } else {
             observations.value.push({ ...newObservation.value });
        }
    }
    newObservation.value = null;
    editingObservationIndex.value = null;
};

const cancelObservation = () => {
    newObservation.value = null;
    editingObservationIndex.value = null;
};

onMounted(() => {
    window.addEventListener('resize', updateScale);
});

onUnmounted(() => {
    window.removeEventListener('resize', updateScale);
});
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
                            <span v-if="mixerNumber">Mixer: {{ mixerNumber }}</span>
                        </div>
                        <div class="flex-fill"></div>
                        <div class="slab-meta-boxes d-flex">
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
                                    {{ selectedSlab.template.split('-').pop().trim() }}
                                </div>
                            </div>
                        </div>
                    </div>



                    <div v-if="!isQAStarted" class="d-flex align-items-center justify-content-center p-5 border rounded"
                        style="min-height: 400px; background: var(--card-bg);">
                        <button class="btn btn-primary btn-lg px-5 font-weight-bold"
                            style="font-size: 1.2rem; transform: scale(1.2);" @click="startProcess()">
                            <span class="fa fa-play mr-2"></span>{{ __('Start Quality Analysis') }}
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
                            <div class="col-md-6 mb-3">
                                <label class="small text-muted">{{ __('Filler Spot') }}</label>
                                <input type="text" v-model="form.fs" class="form-control">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="small text-muted">{{ __('Contamination') }}</label>
                                <input type="text" v-model="form.con" class="form-control">
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
                        <div class="row">
                            <div class="col-12" v-if="slabSize">
                                <div class="visualizer-container position-relative mb-3" 
                                    ref="visualizerRef"
                                    :style="{ 
                                        width: '100%', 
                                        maxWidth: '800px',
                                        aspectRatio: `${slabSize.length} / ${slabSize.breadth}`,
                                        outline: '2px solid var(--text-color)',
                                        background: 'var(--fg-color)',
                                        cursor: 'crosshair',
                                        margin: '0 auto'
                                    }"
                                    @mousemove="handleMouseMove"
                                    @mouseleave="handleMouseLeave"
                                    @click="handleSlabClick">
                                    
                                    <!-- Crosshairs & Labels -->
                                    <template v-if="hoverCoordinates.visible && !newObservation">
                                        <!-- Horizontal Line -->
                                        <div class="crosshair-h" 
                                            :style="{ top: (hoverCoordinates.y * slabScale) + 'px' }">
                                        </div>
                                        
                                        <!-- Vertical Line -->
                                        <div class="crosshair-v" 
                                            :style="{ left: (hoverCoordinates.x * slabScale) + 'px' }">
                                        </div>
                                        
                                        <!-- X Label (Left Distance) -->
                                        <div class="crosshair-label label-x"
                                            :style="{ 
                                                top: (hoverCoordinates.y * slabScale) + 'px',
                                                left: (hoverCoordinates.x * slabScale) + 'px'
                                            }">
                                            {{ hoverCoordinates.x }} mm
                                        </div>
                                        
                                        <!-- Y Label (Top Distance) -->
                                        <div class="crosshair-label label-y"
                                            :style="{ 
                                                top: (hoverCoordinates.y * slabScale) + 'px',
                                                left: (hoverCoordinates.x * slabScale) + 'px'
                                            }">
                                            {{ hoverCoordinates.y }} mm
                                        </div>
                                    </template>
                                    
                                    <!-- Existing Observations -->
                                    <div v-for="(obs, index) in observations" :key="index"
                                        class="obs-marker"
                                        :style="{
                                            left: (obs.x * slabScale) + 'px',
                                            top: (obs.y * slabScale) + 'px'
                                        }"
                                        :title="`${obs.text} (${obs.x}, ${obs.y})`"
                                        @click.stop="editObservation(index)">
                                        <div class="marker-dot"></div>
                                    </div>
                                    
                                    <!-- New Observation Input -->
                                    <div v-if="newObservation" 
                                        class="obs-input-popup p-2 shadow rounded border"
                                        :style="{
                                            left: (newObservation.x * slabScale) + 'px',
                                            top: (newObservation.y * slabScale) + 'px',
                                            position: 'absolute',
                                            zIndex: 100,
                                            minWidth: '200px',
                                            background: 'var(--card-bg)',
                                            color: 'var(--text-color)',
                                            transform: 'translate(-10px, 10px)'
                                        }"
                                        @click.stop>
                                        <div class="small text-muted mb-1">
                                            {{ newObservation.x }}, {{ newObservation.y }}
                                        </div>
                                        <input id="obs-input" type="text" v-model="newObservation.text" 
                                            class="form-control form-control-sm mb-2" 
                                            :placeholder="__('Enter observation')"
                                            @keydown.enter="saveObservation"
                                            @keydown.esc="cancelObservation">
                                        <div class="d-flex justify-content-end">
                                            <button v-if="editingObservationIndex !== null" 
                                                class="btn btn-xs btn-danger mr-auto" 
                                                @click="deleteObservation">
                                                Delete
                                            </button>
                                            <button class="btn btn-xs btn-light mr-1" @click="cancelObservation">Cancel</button>
                                            <button class="btn btn-xs btn-primary" @click="saveObservation">Save</button>
                                        </div>
                                    </div>
                                    
                                </div>
                                <div class="text-center text-muted small mt-2">
                                    {{ __('Click anywhere on the slab to add an observation point.') }}
                                </div>
                            </div>
                            <div class="col-12 text-center py-5 text-muted" v-else>
                                {{ __('Slab dimensions not available for visualization.') }}
                            </div>
                        </div>

                        <!-- Others -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Grading & Remarks') }}</h5>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Bend (mm)') }}</label>
                                <input type="number" v-model="form.bend" class="form-control">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Grade') }}</label>
                                <select v-model="form.grade" class="form-control" required>
                                    <option value="">{{ __('Select Grade') }}</option>
                                    <option v-for="g in grades" :key="g.name" :value="g.name">
                                        {{ g.grade_name }}
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Remarks') }}</label>
                                <textarea v-model="form.remarks" class="form-control" rows="1"></textarea>
                            </div>
                        </div>

                        <div class="mt-4 border-top pt-4 d-flex justify-content-end align-items-center">
                            <div class="actions">
                                <button class="btn btn-primary btn-lg px-5" @click="confirmAndTag">
                                    <span class="fa fa-check mr-2"></span>{{ __('Submit Quality Report') }}
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

<style scoped>
.obs-marker {
    position: absolute;
    width: 0;
    height: 0;
}

.marker-dot {
    width: 12px;
    height: 12px;
    background: #dc3545; /* Red */
    border: 2px solid white;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    /* cursor: pointer; */
}


.marker-dot:hover {
    transform: translate(-50%, -50%) scale(1.2);
}

.crosshair-h {
    position: absolute;
    width: 100%;
    height: 1px;
    left: 0;
    border-top: 1px dashed var(--text-color);
    pointer-events: none;
    z-index: 10;
}

.crosshair-v {
    position: absolute;
    height: 100%;
    width: 1px;
    top: 0;
    border-left: 1px dashed var(--text-color);
    pointer-events: none;
    z-index: 10;
}

.crosshair-label {
    position: absolute;
    background: var(--text-color);
    color: var(--card-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    pointer-events: none;
    z-index: 11;
    white-space: nowrap;
}

.label-x {
    transform: translate(-100%, -50%);
    margin-left: -30px;
}

.label-y {
    transform: translate(-50%, -100%);
    margin-top: -30px;
}
</style>
