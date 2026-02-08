<script setup>
import { ref, reactive, nextTick, computed, onMounted, onUnmounted } from 'vue';

const jobCardNumber = ref(null);
const ovenData = ref(null);
const selectedSlab = ref(null);
const currentTime = ref(new Date());
let timerInterval = null;
const overheat_minutes = 90; // TODO: This should be replaced by a setting in Mahi Granites Settings.


const racks = computed(() => {
    if (!ovenData.value || !ovenData.value.racks) return [];

    return ovenData.value.racks.map(r => {
        // Calculate time_text if curing
        let time_text = '';
        if ((r.status === 'Heating' || r.status === 'Overheat') && r.start_time) {
            const start = new Date(r.start_time.replace(' ', 'T'));
            const now = currentTime.value;
            const diffMs = now - start;

            if (diffMs > 0) {
                const diffSec = Math.floor(diffMs / 1000);
                const mm = Math.floor(diffSec / 60).toString().padStart(2, '0');
                const ss = (diffSec % 60).toString().padStart(2, '0');
                time_text = `${mm}:${ss}`;
            } else {
                time_text = "00:00";
            }

            // If the total time elapsed is greater than overheat_minutes, set status to Overheat
            if (diffMs > overheat_minutes * 60 * 1000) {
                r.status = 'Overheat';
            }
        }

        return {
            name: r.name,
            slot: r.rack_number,
            state: r.status,
            slab: r.current_slab,
            color: r.current_slab_template || "KY1005-J-20",
            is_operational: r.is_operational,
            time_text: time_text,
        };
    });
});

const oven = computed(() => {
    return ovenData.value;
});

const ovenTemps = computed(() => {
    if (!ovenData.value) return { upper: 0, lower: 0 };
    return {
        upper: ovenData.value.slab_top_temp,
        lower: ovenData.value.slab_bottom_temp
    };
});

const showMeasureModal = ref(false);
const targetRack = ref(null);
const measurements = ref({
    tl: 0, tr: 0, bl: 0, br: 0,
    tm: 0, bm: 0, lm: 0, rm: 0
});

const showUnloadModal = ref(false);
const unloadValues = ref({
    slab_top_temp: 0,
    slab_bottom_temp: 0,
    remarks: ''
});
const currentSlab = ref(null);
const loadingSlab = ref(false);

const work_context = reactive({
    role: "Oven Operator",
    assigned_line: "",
    assigned_station: "Oven 1",
    assigned_shift: ""
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

const refreshOvenData = async () => {
    if (!work_context?.assigned_line) {
        return
    }

    try {
        const r = await frappe.call({
            method: 'erpnext.manufacturing.doctype.oven.api.get_oven_from_line',
            args: {
                line: work_context.assigned_line,
            }
        });

        if (r.message) {
            ovenData.value = r.message;
        }
    } catch (e) {
        console.error("Failed to fetch oven data", e);
    }
};

const fetch_slab_for_job_card = async (play_ding = false) => {
    loadingSlab.value = true;
    try {
        const result = await frappe.call({
            method: 'erpnext.manufacturing.page.operator_station.operator_station.get_next_work_item',
            args: {
                process: "Heating",
                line: work_context.assigned_line,
                include_wip: false
            }
        });

        if (!selectedSlab.value && result.message?.slab && play_ding) {
            erpnext.utils.play_ding("new_slab");
        }

        selectedSlab.value = result.message?.slab;
        jobCardNumber.value = result.message?.job_card?.name;
    } catch (e) {
        console.error("Failed to fetch slab for job card", e);
    } finally {
        loadingSlab.value = false;
    }
};

onMounted(async () => {
    const route = frappe.get_route();
    jobCardNumber.value = route[1] || null;

    timerInterval = setInterval(() => {
        currentTime.value = new Date();
    }, 1000);

    await fetchWorkContext();
    await refreshOvenData();
    await fetch_slab_for_job_card();
});

onUnmounted(() => {
    if (timerInterval) clearInterval(timerInterval);
});

function loadIntoRack(rack) {
    if (rack.state !== 'Idle' || !rack.is_operational) return;

    if (!selectedSlab.value) {
        frappe.msgprint(__('Please select an incoming slab or ensure Job Card is active.'));
        return;
    }

    // Prepare for modal
    targetRack.value = rack;
    // Reset measurements
    measurements.value = {
        tl: 0, tr: 0, bl: 0, br: 0,
        tm: 0, bm: 0, lm: 0, rm: 0
    };

    showMeasureModal.value = true;

    nextTick(() => {
        const el = document.getElementById('pos-tl');
        if (el) el.select();
    });
}

async function unload_slab_from_rack(rack) {
    if (rack.state !== 'Heating' && rack.state !== 'Overheat' || !rack.is_operational) return;

    targetRack.value = rack;
    unloadValues.value = {
        slab_top_temp: undefined,
        slab_bottom_temp: undefined,
        remarks: ''
    };
    showUnloadModal.value = true;
}

async function confirmUnload() {
    if (!targetRack.value) return;

    if (unloadValues.value.slab_top_temp === undefined || unloadValues.value.slab_top_temp === '' || unloadValues.value.slab_top_temp === null) {
        frappe.msgprint(__('Please enter Slab Top Temperature'));
        return;
    }
    if (unloadValues.value.slab_bottom_temp === undefined || unloadValues.value.slab_bottom_temp === '' || unloadValues.value.slab_bottom_temp === null) {
        frappe.msgprint(__('Please enter Slab Bottom Temperature'));
        return;
    }

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.doctype.oven.api.unload_slab_from_oven',
            args: {
                rack_name: targetRack.value.name,
                slab_name: targetRack.value.slab,
                slab_template: targetRack.value.color,
                values: unloadValues.value
            }
        });

        if (res.message) {
            await refreshOvenData();
            await fetch_slab_for_job_card(true);
            frappe.show_alert({ message: __('Slab unloaded to the next process successfully'), indicator: 'green' });
            erpnext.utils.play_ding("submit");
        }
    } catch (e) {
        console.error(e);
    }

    showUnloadModal.value = false;
    targetRack.value = null;
}

async function confirmLoad() {
    if (!targetRack.value || !ovenData.value) {
        return;
    }

    prepareOvenOperation();
    const res = await frappe.call({
        method: 'erpnext.manufacturing.doctype.oven.api.load_slab_into_oven',
        args: {
            oven_op: ovenOperation.value,
            job_card_name: jobCardNumber.value || selectedSlab.value?.current_job_card,
            slab_template: selectedSlab.value?.template,
        }
    })

    if (res && res.message) {
        frappe.show_alert({ message: __('Slab loaded and heating started'), indicator: 'green' });
        await refreshOvenData();
        await fetch_slab_for_job_card(true);
    }

    // remove slab from incoming list or clear selected if single Job Card
    if (Array.isArray(currentSlab.value)) {
        const idx = currentSlab.value.findIndex(s => s.name === selectedSlab.value?.name);
        if (idx !== -1) currentSlab.value.splice(idx, 1);
    }
    selectedSlab.value = null;

    closeModal();
}

function closeModal() {
    showMeasureModal.value = false;
    targetRack.value = null;
}

function editTemperatures() {
    const fields = [
        { label: 'Upper Shelf (°C)', fieldname: 'upper', fieldtype: 'Int', default: ovenTemps.value.upper },
        { label: 'Lower Shelf (°C)', fieldname: 'lower', fieldtype: 'Int', default: ovenTemps.value.lower }
    ];

    frappe.prompt(fields, (values) => {
        if (!ovenData.value) return;

        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'Oven',
                name: ovenData.value.name,
                fieldname: {
                    slab_top_temp: values.upper,
                    slab_bottom_temp: values.lower
                }
            }
        }).then(() => refreshOvenData());

    }, __('Update Oven Temperatures'), __('Update'));
}

function rackClasses(rack) {
    if (rack.state === 'Heating') return 'curing';
    if (rack.state === 'Overheat') return 'overheat';
    if (!rack.is_operational) return 'maintenance';
    
    // Idle state
    if (!selectedSlab.value) return 'disabled empty';
    return 'empty';
}

// const oven = get_oven_details(work_context.assigned_station);
const ovenOperation = ref({});

function prepareOvenOperation() {
    if (!ovenData.value || !selectedSlab.value || !targetRack.value) return;

    ovenOperation.value = {
        doctype: 'Oven Operation',
        oven: ovenData.value.name,
        date: frappe.datetime.now_datetime(),
        shift: work_context.assigned_shift,
        slab: selectedSlab.value?.name,
        slab_color: selectedSlab.value?.template,
        oven_rack: targetRack.value.name,
        upper_shelf_temp: ovenTemps.value.upper,
        lower_shelf_temp: ovenTemps.value.lower,
        top_left_vertex: measurements.value.tl,
        top_edge_center: measurements.value.tm,
        top_right_vertex: measurements.value.tr,
        right_edge_centre: measurements.value.rm,
        bottom_right_vertex: measurements.value.br,
        bottom_edge_centre: measurements.value.bm,
        bottom_left_vertex: measurements.value.bl,
        left_edge_centre: measurements.value.lm,
        remarks: ''
    };
}

frappe.realtime.on('slab_checkout', async (slab) => {
    // If the slab has been checked out on a different line or the status of the checked out slab is not 'Pressing', then ignore the event.
    if (slab.line !== work_context.assigned_line || slab.status !== 'Pressing') {
        return;
    }

    if (!selectedSlab.value) {
        await refreshOvenData();
        await fetch_slab_for_job_card(true);
    }
});

</script>

<template>
    <div class="page-card d-flex">
        <!-- Center: Oven Monitor -->
        <div class="flex-fill pl-4">
            <div class="border-bottom d-flex justify-content-between pb-2">
                <div>
                    <h4 class="mb-1">{{ __('Oven') }}: {{ oven?.name }} <span class="text-muted mr-2 ml-2">|</span> {{
                        __('Line') }}: {{ oven?.line }}
                    </h4>
                    <div class="text-muted small mb-4">
                        {{ __('Manage curing process and rack assignments.') }}
                    </div>
                </div>

                <div class="ml-4 mb-3 d-flex align-items-center cursor-pointer" @click="editTemperatures"
                    title="Click to update">
                    <div class="temp-badge mr-3">
                        <span class="text-muted small mr-1">{{ __('Upper') }}:</span>
                        <span class="font-weight-bold temp-text">{{ ovenTemps.upper }}°C</span>
                    </div>
                    <div class="temp-badge">
                        <span class="text-muted small mr-1">{{ __('Lower') }}:</span>
                        <span class="font-weight-bold temp-text">{{ ovenTemps.lower }}°C</span>
                    </div>
                </div>

                <div class="d-flex mb-4 justify-content-end align-items-center">
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#b0b8bf; width:1rem; height:1rem;"></span>{{ __('Empty') }}
                    </span>
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#2bc63b; width:1rem; height:1rem;"></span>{{ __('Curing') }}
                    </span>
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#ef1e3f; width:1rem; height:1rem;"></span>{{ __('Overheating') }}
                    </span>
                    <span class="small d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#77afe6; width:1rem; height:1rem;"></span>{{ __('Maintenance') }}
                    </span>
                </div>
            </div>

            <Transition name="pop-switch" mode="out-in">
                <div v-if="selectedSlab" key="current-slab" class="current-slab-container d-flex align-items-center justify-content-between border rounded p-3 mb-4 mt-3" style="background-color: var(--control-bg-on-gray, #e2edff); border-color: var(--primary-color) !important;">
                    <div class="d-flex align-items-center">
                        <span class="text-muted mr-3">{{ __('Current Slab') }}:</span>
                        <div class="slab-thumbnail mr-3" style="width: 24px; height: 24px;"></div>
                        <span class="font-weight-bold h5 mb-0 mr-2">{{ selectedSlab.name }}</span>
                        <span class="text-muted">{{ selectedSlab.template }}</span>
                    </div>
                </div>
                <div v-else key="no-slabs" class="no-slabs-message d-flex align-items-center justify-content-center border rounded p-3 mb-4 mt-3 text-muted">
                    {{ __('No slabs available for heating') }}
                </div>
            </Transition>

            <div class="rack-grid d-flex flex-wrap" :class="selectedSlab ? 'pt-3' : 'pt-5'">
                <div v-for="rack in racks" :key="rack.slot" :class="rackClasses(rack)" class="rack-card mb-3 mr-3 p-3 rounded"
                    style="position: relative;"
                    @click="rack.state === 'Heating' || rack.state === 'Overheat' ? unload_slab_from_rack(rack) : loadIntoRack(rack)">
                    <div v-if="rack.state === 'Overheat'" class="warning-icon pulse-icon">
                        <span class="fa fa-exclamation-circle text-danger"></span>
                    </div>
                    <div class="strong mb-1" style="position: absolute;">{{ rack.slot }}</div>
                    <div class="d-flex align-items-center justify-content-center flex-fill">
                        <!-- empty -->
                        <div v-if="rack.state === 'Idle' && rack.is_operational" class="text-center text-muted">
                            <div class="mb-3"><span class="fa fa-inbox" style="font-size:1.5rem;"></span></div>
                            <div class="font-weight-bold">{{ __('LOAD HERE') }}</div>
                        </div>
                        <!-- curing -->
                        <div v-else-if="(rack.state === 'Heating' || rack.state === 'Overheat') && rack.is_operational"
                            class="text-center">
                            <div class="font-weight-bold mb-1">{{ rack.slab }}</div>
                            <div class="text-muted small mb-1">{{ rack.color }}</div>
                            <div class="text-muted small" v-if="rack.state === 'Heating'">
                                <span class="fa fa-clock-o mr-1"></span>{{ rack.time_text }}
                            </div>
                            <div class="text-danger strong" v-if="rack.state === 'Overheat'">
                                <span class="fa fa-thermometer-full mr-1 pulse-icon"></span>{{ rack.time_text }}
                            </div>
                        </div>
                        <!-- overheat -->
                        <!-- <div v-else-if="rack.state === 'Overheat' && rack.is_operational" class="text-center">
                            <div class="font-weight-bold mb-1">{{ rack.slab }}</div>
                            <div class="text-muted small mb-1">{{ rack.color }}</div>
                            <div class="text-danger small">
                                <span class="fa fa-thermometer-full mr-1"></span>{{ rack.time_text }}
                            </div>
                        </div> -->
                        <!-- maintenance -->
                        <div v-else-if="!rack.is_operational" class="text-center text-muted">
                            <div class="mb-2">
                                <span class="fa fa-exclamation-triangle mr-1" style="font-size:1.4rem;"></span>
                            </div>
                            <div class="font-weight-bold">{{ __('MAINTENANCE') }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Slab Measure Modal Overlay -->
    <div v-if="showMeasureModal" class="modal-backdrop-custom d-flex align-items-center justify-content-center">
        <div class="modal-card shadow-lg rounded p-4" style="width: 600px;">
            <h5 class="mb-3">{{ __('Verify Dimensions') }}</h5>
            <p class="text-muted small mb-5">
                {{ __('Measure 8 points on the slab before loading.') }}
                <br>
                <!-- {{ selectedSlab }} &rarr; {{ targetRack?.slot }} -->
            </p>

            <div class="measure-container d-flex justify-content-center align-items-center mb-4" v-if="selectedSlab">
                <!-- The geometric representation -->
                <div class="slab-rect position-relative border">
                    <!-- Top Left -->
                    <input id="pos-tl" type="number" v-model.number="measurements.tl"
                        class="meas-input pos-tl form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Top -->
                    <input id="pos-tm" type="number" v-model.number="measurements.tm"
                        class="meas-input pos-tm form-control input-sm" @click="$event.target.select()">
                    <!-- Top Right -->
                    <input id="pos-tr" type="number" v-model.number="measurements.tr"
                        class="meas-input pos-tr form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Right -->
                    <input id="pos-rm" type="number" v-model.number="measurements.rm"
                        class="meas-input pos-rm form-control input-sm" @click="$event.target.select()">
                    <!-- Bottom Right -->
                    <input id="pos-br" type="number" v-model.number="measurements.br"
                        class="meas-input pos-br form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Bottom -->
                    <input id="pos-bm" type="number" v-model.number="measurements.bm"
                        class="meas-input pos-bm form-control input-sm" @click="$event.target.select()">
                    <!-- Bottom Left -->
                    <input id="pos-bl" type="number" v-model.number="measurements.bl"
                        class="meas-input pos-bl form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Left -->
                    <input id="pos-lm" type="number" v-model.number="measurements.lm"
                        class="meas-input pos-lm form-control input-sm" @click="$event.target.select()">

                    <div class="text-center strong mt-5 pt-5">{{ selectedSlab.name }}</div>
                </div>
            </div>

            <div class="d-flex justify-content-end pt-4">
                <button class="btn btn-secondary mr-2" @click="closeModal">{{ __('Cancel') }}</button>
                <button class="btn btn-primary" @click="confirmLoad">{{ __('Load Slab') }}</button>
            </div>
        </div>
    </div>

    <!-- Slab Unload Modal Overlay -->
    <div v-if="showUnloadModal" class="modal-backdrop-custom d-flex align-items-center justify-content-center">
        <div class="modal-card shadow-lg rounded p-4" style="width: 500px;">
            <h5 class="mb-3">{{ __('Unload Slab') }}</h5>
            <div class="text-muted small mb-4">
                {{ targetRack?.slab }} &bull; {{ targetRack?.color }}
            </div>

            <div class="form-group mb-3">
                <label class="small text-muted">{{ __('Slab Top Temperature') }} <span
                        class="text-danger">*</span></label>
                <input type="number" v-model.number="unloadValues.slab_top_temp" class="form-control">
            </div>
            <div class="form-group mb-3">
                <label class="small text-muted">{{ __('Slab Bottom Temperature') }} <span
                        class="text-danger">*</span></label>
                <input type="number" v-model.number="unloadValues.slab_bottom_temp" class="form-control">
            </div>
            <div class="form-group mb-4">
                <label class="small text-muted">{{ __('Remarks') }}</label>
                <textarea v-model="unloadValues.remarks" class="form-control" rows="3"></textarea>
            </div>

            <div class="d-flex justify-content-end">
                <button class="btn btn-secondary mr-2" @click="showUnloadModal = false">{{ __('Cancel') }}</button>
                <button class="btn btn-primary" @click="confirmUnload">{{ __('Confirm Unload') }}</button>
            </div>
        </div>
    </div>

</template>

<style scoped>
.page-card {
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.incoming-item {
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

.rack-card {
    border: 2px dashed var(--border-color, #ced4da);
    background: var(--control-bg, #f8f9fa);
    width: 225px;
    height: 120px;
    display: flex;
    flex-direction: column;
    transition: all 0.2s ease;
}

.rack-card:hover {
    cursor: pointer;
    border-color: var(--primary-color, #74c0fc) !important;
    box-shadow: 0 0 0 3px rgba(116, 192, 252, 0.4);
}

.rack-card.empty {
    border-style: dashed;
    border-color: var(--border-color, #ced4da);
    background: var(--control-bg, #f8f9fa);
}

.rack-card.curing {
    border-style: solid;
    border-color: #28a745;
    background: rgba(40, 167, 69, 0.15); /* Green tint */
}

.rack-card.overheat {
    border-style: solid;
    border-color: #dc3545;
    background: rgba(220, 53, 69, 0.15); /* Red tint */
}

.rack-card.maintenance {
    border-style: dashed;
    border-color: #6c757d;
    background: rgba(108, 117, 125, 0.15); /* Gray tint */
}

.rack-card.disabled {
    opacity: 0.5;
    cursor: not-allowed !important;
    pointer-events: none;
}

.temp-badge {
    background: var(--bg-color, #fff);
    border: 1px solid var(--border-color, #dee2e6);
    padding: 4px 10px;
    border-radius: 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    cursor: pointer;
}

.modal-backdrop-custom {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1050;
}

.modal-card {
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.slab-rect {
    width: 300px;
    height: 180px;
    /* background: #f1f3f5; */
    border: 3px solid var(--text-color, #333) !important;
}

.meas-input {
    position: absolute;
    width: 60px;
    text-align: center;
    padding: 2px;
    font-size: 12px;
}

.temp-text {
    color: var(--text-success, green);
}

.incoming-list {
    width: 250px;
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
    background: var(--gray-800, #1f2937);
}

/* Positions for inputs */
/* Corners */
.pos-tl {
    top: -15px;
    left: -30px;
}

.pos-tr {
    top: -15px;
    right: -30px;
}

.pos-bl {
    bottom: -15px;
    left: -30px;
}

.pos-br {
    bottom: -15px;
    right: -30px;
}

/* Mids - centered on edges */
/* Horizontal mids: left: 50% - half width (30px) */
.pos-tm {
    top: -15px;
    left: calc(50% - 30px);
}

.pos-bm {
    bottom: -15px;
    left: calc(50% - 30px);
}

/* Vertical mids: top: 50% - half height (~15px for input height approx) */
/* Actually input height is maybe 30px? let's center vertically */
.pos-lm {
    top: calc(50% - 15px);
    left: -30px;
}

.pos-rm {
    top: calc(50% - 15px);
    right: -30px;
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

@keyframes pulse {
    0% {
        transform: scale(1);
    }

    50% {
        transform: scale(1.2);
    }

    100% {
        transform: scale(1);
    }
}

.pulse-icon {
    animation: pulse 1s infinite;
    display: inline-block;
}

.warning-icon {
    position: absolute;
    top: -10px;
    right: -10px;
    background: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    border: 2px solid #e03636 !important
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
