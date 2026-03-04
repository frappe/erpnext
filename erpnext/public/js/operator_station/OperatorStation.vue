<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue';

const jobCardName = ref(null);
const jobCardDoc = ref(null);
const status = ref('Pending');
const colour = ref('');

const processStarted = ref(false);
const processStartTime = ref(null);
const processElapsed = ref(0);
const processTimerHandle = ref(null);
const processReady = ref(true);

const slabNumber = ref(null);
const jobCardSubmitted = ref(false);
const preparedQty = ref(0);
const stockEntryName = ref('');
const transferredQty = ref(0);
const transferSuccess = ref(false);
const nextWorkOrder = ref('');
const slabTemplate = ref('');
const line = ref(null);
const error = ref(null);
const batchNo = ref(null);
const mixerNumber = ref(null);
const slabsQueue = ref([]);
const is_standalone = ref(false);
const availableSlabsCount = ref(0);
const availableJobCardsCount = ref(0);
const isProcessing = ref(false);
const isRepressed = ref(false);
const currentStation = ref(null);

const alarms = ref([
	{
		station: 'Polishing 1',
		type: 'QUALITY ISSUE',
		description: 'Surface defect detected on SLB-2025-00425',
		time: '14:23:15',
		tone: 'danger'
	},
	{
		station: 'Trimmer',
		type: 'MACHINE PROBLEM',
		description: 'Blade alignment issue',
		time: '14:15:42',
		tone: 'warning'
	}
]);

const station_reverse_map = {
	"pressing": "Distribution",
	"cooling": "Heating",
	"trimming": "Quarantine",
	"calibration": "Trimming",
	"polishing": "Calibration",
};

const work_context = reactive({
	role: "Oven Operator",
	assigned_line: "",
	assigned_station: "Oven 1",
	assigned_shift: ""
});

const fetchWorkContext = async () => {
	const route = frappe.get_route();
	const station = route[1] || '';
	currentStation.value = station.toLowerCase();

	const currentUser = await frappe.call({
		method: "erpnext.setup.doctype.employee.api.get_current_user_context",
	});

	if (currentUser.message) {
		work_context.role = currentUser.message.designation;
		work_context.assigned_line = currentUser.message.production_line;
		work_context.assigned_shift = currentUser.message.attendance_shift;
	}
};

// UI flags
const showAlarms = ref(true);

const lastThickness = ref(null);

function showThicknessConfirmationDialog(oldThick, newThick) {
	let d = new frappe.ui.Dialog({
		title: __('Thickness Changed'),
		fields: [
			{
				fieldname: 'msg',
				fieldtype: 'HTML',
				options: `<div class="text-center" style="font-size: 1.2rem; margin: 15px 0;">
					<span class="fa fa-exclamation-triangle text-warning" style="font-size: 2rem; margin-bottom: 10px; display: block;"></span>
					<p>${__('The slab thickness has changed from')} <b>${oldThick}</b> ${__('to')} <b>${newThick}</b>.</p>
					<p class="text-muted" style="font-size: 1rem;">${__("Please confirm that the machine's settings have been adjusted accordingly.")}</p>
				</div>`
			}
		],
		primary_action_label: __('Yes, I confirm'),
		primary_action: function() {
			d.hide();
		}
	});

	if (d.get_close_btn()) {
		d.get_close_btn().hide();
	}

	d.$wrapper.modal({ backdrop: 'static', keyboard: false });
	d.show();
}

function handleThicknessChange(newTemplate) {
	if (!newTemplate) return;
	// If the current process is not Calibration or Polishing do not show the confirmation dialog.
	const route = frappe.get_route();
	const station = (route[1] || '').toLowerCase();
	if (station !== 'calibration' && station !== 'polishing') return;

	const parts = String(newTemplate).split('-');
	if (parts.length >= 3) {
		const newThickness = parts[2];
		if (lastThickness.value && lastThickness.value !== newThickness) {
			showThicknessConfirmationDialog(lastThickness.value, newThickness);
		}

		lastThickness.value = newThickness;
	}
}

watch(() => colour.value, handleThicknessChange);
watch(() => slabTemplate.value, handleThicknessChange);

// Raise‑alarm dialog
const issueDialogOpen = ref(false);
const issueType = ref('Quality Issue');
const issueDescription = ref('');

// formatted timer
const formattedTime = computed(() => {
	const h = String(Math.floor(processElapsed.value / 3600)).padStart(2, '0');
	const m = String(Math.floor((processElapsed.value % 3600) / 60)).padStart(2, '0');
	const s = String(processElapsed.value % 60).padStart(2, '0');
	return `${h}:${m}:${s}`;
});

const isPressing = computed(() => {
	return currentStation.value === 'pressing';
});

const props = defineProps({
	process: {
		type: String,
		default: 'operator'
	},
	job_card: {
		type: String,
		default: null
	}
});

async function loadJobCard(name) {
	if (!name) return;

	jobCardName.value = name;

	try {
		const jc = await frappe.db.get_doc('Job Card', jobCardName.value);
		jobCardDoc.value = jc;

		if (jc.bom_no && !slabTemplate.value) {
			const bom = await frappe.db.get_doc('BOM', jc.bom_no);
			if (bom.slab_template) {
				slabTemplate.value = bom.slab_template;
			}
		}

		jobCardSubmitted.value = jc.docstatus === 1 || jc.status === 'Completed';
		if (jobCardSubmitted.value) {
			preparedQty.value = jc.total_completed_qty || jc.for_quantity || 0;
		}

		const stateRes = await frappe.call({
			method: 'erpnext.manufacturing.page.operator_station.operator_station.get_machine_state',
			args: {
				job_card: jobCardName.value,
				process_name: currentStation.value
			}
		});

		is_standalone.value = !!stateRes?.message?.is_wh_standalone;
		if (is_standalone.value) {
			fetchQueue(work_context.assigned_line, currentStation.value);
		}

		const state = stateRes.message || {};
		status.value = state.status || 'Pending';

		if (status.value === 'Work In Progress') {
			processStarted.value = true;
			processReady.value = false;
		} else {
			processStarted.value = false;
			processReady.value = true;
		}

		processStartTime.value = state[`${currentStation.value}_start_time`];
		mixerNumber.value = state.mixer_number;

		if (jobCardSubmitted.value) {
			stockEntryName.value = state.stock_entry_name || '';
		}

		if (processStarted.value && processStartTime.value) {
			const start = new Date(processStartTime.value);
			const now = new Date()
			const diffSeconds = (now - start) / 1000;
			processElapsed.value = Math.max(0, Math.floor(diffSeconds));

			if (processTimerHandle.value) clearInterval(processTimerHandle.value);
			processTimerHandle.value = setInterval(() => {
				processElapsed.value += 1;
			}, 1000);
		} else {
			processElapsed.value = 0;
			if (processTimerHandle.value) {
				clearInterval(processTimerHandle.value);
				processTimerHandle.value = null;
			}
		}
	} catch (e) {
		frappe.msgprint(__('Failed to load Job Card details.'));
	}
}

async function checkForNextItem() {
	if (!jobCardName.value) {
		await getNextWorkItem(true)
	}
}

const getNextWorkItem = async (play_alert = false) => {
	const result = await frappe.call({
		method: 'erpnext.manufacturing.page.operator_station.operator_station.get_next_work_item',
		args: {
			process: currentStation.value,
			line: work_context.assigned_line || '2' // Defaulting to L1 for now if not known
		}
	});

	if (result.message) {
		res_slab = result.message.slab
		res_job_card = result.message.job_card

		slabNumber.value = res_slab?.name || result.message.job_card?.slab;
		isRepressed.value = res_slab?.is_repressed || false;
		colour.value = res_slab?.template || result.message.job_card?.bom_no;
		batchNo.value = res_slab?.batch_number || result.message.job_card?.slab?.split('-')[0];

		if (res_job_card && res_job_card?.name !== jobCardName.value) {
			if (play_alert && !jobCardName.value) {
				erpnext.utils.play_ding("new_slab");
			}

			await loadJobCard(res_job_card.name);
		}

		const slabs = result.message.available_slabs_count;
		const cards = result.message.available_job_cards_count;
		availableSlabsCount.value = (slabs && slabs > 0) ? (slabs - 1) : 0;
		availableJobCardsCount.value = (cards && cards > 0) ? (cards - 1) : 0;
	}
};

onMounted(async () => {
	try {
		await fetchWorkContext();
		await loadData();

		document.addEventListener("refresh-operator-station", () => {
			loadData();
		});
	} catch (e) {
		error.value = e.message;
		frappe.msgprint(__('Load failed'));
	}
});

async function loadData() {
	if (!jobCardName.value) {
		getNextWorkItem();
	} else {
		await loadJobCard(jobCardName.value);
	}
}

async function fetchQueue(line, station) {
	try {
		slabsQueue.value = [];
		const result = await frappe.call({
			method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_for',
			args: {
				line: line,
				next_stage: station.toLowerCase(),
				limit: 100, // TODO: change this limit
			}
		});
		if (result.message) {
			slabsQueue.value = result.message || [];
		}
	} catch (e) {
		console.error('Failed to fetch queue:');
	}
}

frappe.realtime.on('refresh_operator_station', (data) => {
	const route = frappe.get_route();
	const station = (route[1] || '').toLowerCase();

	if (station === "distribution") {
		checkForNextItem();
	}
});

frappe.realtime.on('slab_checkout', (slab) => {
	// If the slab has been checked out on a different line or the checked out slab is not the previous stage of the current stage, then ignore the event.
	if (slab.line !== work_context.assigned_line || !station_reverse_map[currentStation.value] || slab.status !== station_reverse_map[currentStation.value]) {
		return;
	}

	checkForNextItem();
});


async function startOperation() {
	frappe.confirm(
		__('Start the process now?'),
		async () => {
			isProcessing.value = true;
			try {
				const res = await frappe.call({
					method: 'erpnext.manufacturing.page.operator_station.operator_station.start_process',
					args: {
						job_card: jobCardName.value,
						process_name: currentStation.value,
						slab_template: slabTemplate.value,
						slab_name: slabNumber.value,
					}
				});

				if (res.message) {
					colour.value = res.message.slab_template;
					batchNo.value = res.message.slab_name?.split('-')[0] || '';
					slabNumber.value = res.message.slab_name;
				}

				status.value = 'In Progress';
				processReady.value = false;
				processStarted.value = true;
				processStartTime.value = new Date().toISOString().slice(0, 19).replace('T', ' ');

				processElapsed.value = 0;
				if (processTimerHandle.value) {
					clearInterval(processTimerHandle.value);
				}
				processTimerHandle.value = setInterval(() => {
					processElapsed.value += 1;
				}, 1000);
			}
			catch (e) {
				frappe.msgprint(__('Failed to start Job Card'));
			} finally {
				isProcessing.value = false;
			}
		},
	);
}

async function repressSlab() {
	if (!currentStation.value || currentStation.value !== "pressing") {
		return;
	}

	frappe.confirm(
		__('Are you sure you want to re-press this slab?'),
		async () => {
			isProcessing.value = true;
			try {
				const result = await frappe.call({
					method: 'erpnext.manufacturing.doctype.slab.api.re_press_slab',
					args: {
						slab_number: slabNumber.value,
					},
				});

				erpnext.utils.play_ding("submit");

			} catch (e) {
				frappe.msgprint(__('Failed to repress slab'));
			} finally {
				isProcessing.value = false;
			}
		}
	);
}

async function finishOperation() {
	frappe.confirm(
		__('Are you sure you want to finish this job?'),
		async () => {
			isProcessing.value = true;

			if (processTimerHandle.value) {
				clearInterval(processTimerHandle.value);
				processTimerHandle.value = null;
			}

			try {
				const transferMaterials = currentStation.value.toLowerCase() !== 'cooling';

				const result = await frappe.call({
					method: 'erpnext.manufacturing.page.operator_station.operator_station.finish_process',
					args: {
						job_card: jobCardName.value,
						process_name: currentStation.value,
						transfer_materials: transferMaterials,
					},
				});

				erpnext.utils.play_ding("submit");

				jobCardName.value = null;
				processStarted.value = false;
				processStartTime.value = null;
				processElapsed.value = 0;
				processReady.value = false;

				jobCardSubmitted.value = true;
				preparedQty.value = result.message.job_card_qty;
				stockEntryName.value = result.message.stock_entry;
				nextWorkOrder.value = result.message.next_work_order || '';
				transferredQty.value = 0;
				transferSuccess.value = false;
				slabNumber.value = null;
				batchNo.value = null;
				colour.value = null;
				isRepressed.value = false;

				await checkForNextItem();
			} catch (error) {
				const errorMsg = error.message || (error._server_messages?.[0]?.message) || JSON.stringify(error);
				frappe.msgprint({
					title: __('Error'),
					indicator: 'red',
					message: `Failed to complete Job Card`
				});
			} finally {
				isProcessing.value = false;
			}
		}
	);
}

function haltJob() {
	status.value = 'Halted';
	if (processTimerHandle.value) {
		clearInterval(processTimerHandle.value);
		processTimerHandle.value = null;
	}
	frappe.msgprint(__('Job is halted'));
}

function discardJob() {
	frappe.confirm(
		__('Are you sure you want to discard this job?'),
		() => {
			stopAndResetTimer();
			status.value = 'Pending'; // Reset to Pending so Start button appears
			processReady.value = true;
			jobCardSubmitted.value = false;
			frappe.msgprint(__('Job is discarded'));
		}
	);
}

function stopAndResetTimer() {
	if (processTimerHandle.value) {
		clearInterval(processTimerHandle.value);
		processTimerHandle.value = null;
	}
	processStarted.value = false;
	processElapsed.value = 0;
	processStartTime.value = null;
}

function toggleAlarms() {
	showAlarms.value = !showAlarms.value;
}

function openIssueDialog() {
	issueDialogOpen.value = true;
}

function submitIssue() {
	const now = new Date().toLocaleTimeString('en-GB');
	alarms.value.unshift({
		station: 'Mixer',
		type: issueType.value.toUpperCase(),
		description: issueDescription.value,
		time: now,
		tone: 'warning'
	});
	issueDialogOpen.value = false;
	issueDescription.value = '';
	frappe.msgprint(__('Alarm submitted'));
}

function statusStyle() {
	if (status.value === 'In Progress') {
		return 'background:#d4f8d4;color:#137a13';
	}
	if (status.value === 'Halted') {
		return 'background:#ffeeba;color:#856404';
	}
	if (status.value === 'Discarded') {
		return 'background:#f8d7da;color:#721c24';
	}
	return 'background:#e9ecef;color:#6c757d';
}

async function selectSlab(slab) {
	if (!slab) return;

	slabNumber.value = slab.name;
	colour.value = slab.template;
	batchNo.value = slab.batch_number;

	// Reset job card state if selecting a new slab manually
	jobCardName.value = null;
	jobCardDoc.value = null;
	status.value = 'Pending';
	processStarted.value = false;
	processReady.value = true;

	try {
		isProcessing.value = true;
		const r = await frappe.call({
			method: 'erpnext.manufacturing.page.operator_station.operator_station.get_job_card_for_slab',
			args: {
				slab_name: slab.name,
				process_name: currentStation.value
			}
		});

		if (r.message?.name) {
			await loadJobCard(r.message.name);
		} else {
			frappe.show_alert({
				message: __('No open Job Card found for this slab'),
				indicator: 'orange'
			});
		}
	} catch (e) {
		console.error(e);
	} finally {
		isProcessing.value = false;
	}
}
</script>
<template>

	<!-- Sidebar: Queue -->
	<div class="operator-station-container d-flex h-100 w-100">

		<div v-if="is_standalone" class="queue-sidebar border-right p-3" style="width: 300px; overflow-y: auto;">
			<h5 class="mb-3 font-weight-bold text-center border-bottom pb-2">
				{{ __('Incoming Slabs') }}
			</h5>

			<div v-if="slabsQueue.length === 0" class="text-muted text-center py-4 rounded border empty-queue-state">
				<span class="fa fa-inbox fa-2x mb-2 d-block text-muted-light"></span>
				{{ __('No slabs in queue') }}
			</div>

			<div v-else>
				<div v-for="item in slabsQueue" :key="item.name" @click="selectSlab(item)"
					class="card pointer mb-2 shadow-sm slab-card border-0">
					<div class="card-body p-3 border-left-3 d-flex justify-content-between align-items-start"
						style="height: 5rem">
						<div>
							<h6 class="card-title mb-1 font-weight-bold">{{ item.batch_number }} - {{ item.serial_number
							}}</h6>
							<div class="small text-muted mb-1">
								<span class="fa fa-cube mr-1"></span>{{ item.template }}
							</div>

						</div>
						<div class="mt-2 text-right">
							<span class="badge border item-time-badge">{{ new
								Date(item.modified).toLocaleTimeString('en-GB') }}</span>
						</div>
					</div>
				</div>
			</div>

		</div>

		<div class="page-card p-0 d-flex h-100 w-100 justify-content-center">
			<div class="operator-station page-card d-flex flex-column align-items-center flex-grow-1 p-4"
				style="overflow-y: auto;">
				<!-- Current Job Card -->
				<Transition name="pop-switch" mode="out-in">
					<div v-if="jobCardName || slabNumber" key="job-card"
						class="current-job-card active-job-card mb-4 w-50 rounded p-4" style="min-width: 650px;">
						<div class="status text-center mb-2" style="font-size:1rem">
							<span class="badge badge-pill" :style="statusStyle()">
								{{ __(status) }}
							</span>
							<span class="badge badge-pill repressed-badge ml-2" v-if="isRepressed">
								{{ __('Re-Pressing') }}
							</span>
						</div>

						<!--<div class="text-center text-muted small">{{ __('SERIAL NUMBER') }}</div>-->
						<h2 class="job-serial text-center font-weight-bold mb-0 p-3">
							{{ slabNumber || batchNo }}
						</h2>

						<!-- Add here -->
						<div v-if="availableJobCardsCount > 0 || availableSlabsCount > 0"
							class="alert alert-danger text-center mb-2 py-1 px-3 mx-auto"
							style="border-radius:20px; font-size: 0.9rem; width: fit-content; display: table; border: 1px solid var(--alert-text-danger)">
							<span class="fa fa-info-circle mr-1"></span>
							<span>
								{{ __('{0} more pending in the queue', [availableSlabsCount || availableJobCardsCount]) }}
							</span>
						</div>
						<h3 class="job-serial text-center font-weight-bold mb-2 p-3">
							{{ jobCardName }}
						</h3>

						<!-- <div class="text-center text-muted small mb-1">{{ __('Colour') }}</div> -->
						<div class="d-flex justify-content-center align-items-center mb-3">
							<span class="job-color bold mr-2" style="font-size:1rem">{{ colour || slabTemplate }}</span>
							<!-- <span class="color-swatch"
								style="width:24px;height:24px;border-radius:4px;background:#f5f5f5;border:1px solid #ddd;"></span> -->
						</div>

						<div v-if="mixerNumber" class="text-center font-weight-bold mb-2 text-muted"
							style="font-size:1rem">
							Mixer: {{ mixerNumber }}
						</div>

						<div class="text-center mb-2" v-if="processReady">
							<button class="btn btn-success py-3 px-4" :disabled="isProcessing" @click="startOperation">
								<span v-if="isProcessing" class="fa fa-spinner fa-spin mr-1 pr-2"></span>
								<span v-else class="fa fa-play mr-1 pr-2"></span>{{ __('Start Job') }}
							</button>
						</div>

						<div class="text-center mb-3" v-if="processStarted && !jobCardSubmitted">
							<div class="text-success" style="font-size:1.5rem">
								<span class="fa fa-clock-o mr-1"></span>
								<span class="job-timer">{{ formattedTime }}</span>
							</div>
						</div>

						<div class="text-center mb-2" v-if="processStarted">
							<button class="btn btn-info py-3 px-4 mr-5" :disabled="isProcessing" @click="finishOperation">
								<span v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></span>
								<span v-else class="fa fa-check-square-o mr-1"></span>{{ __('Finish Job') }}
							</button>
							<button class="btn btn-warning py-3 px-4 mr-5" v-if="isPressing" :disabled="isProcessing" @click="repressSlab">
								<span v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></span>
								<span v-else class="fa fa-retweet mr-1"></span>{{ __('Re-press') }}
							</button>
							<!-- <button class="btn btn-warning py-3 px-4 mr-5" @click="haltJob">
							<span class="fa fa-pause-circle-o mr-1"></span>{{ __('Halt Job') }}
						</button> -->
							<button class="btn btn-danger py-3 px-4" @click="discardJob">
								<span class="fa fa-trash-o mr-1"></span>{{ __('Discard') }}
							</button>
						</div>
					</div>
					<div v-else key="empty-state"
						class="empty-state mb-4 border border-secondary rounded p-5 d-flex flex-column align-items-center justify-content-center"
						style="min-width: 650px; background-color: var(--fg-color); border-style: dashed !important;">
						<div class="mb-3 text-muted" style="opacity: 0.5;">
							<span class="fa fa-inbox" style="font-size: 4rem;"></span>
						</div>
						<h4 class="text-muted font-weight-bold">{{ __('No active job cards') }}</h4>
						<p class="text-muted mb-0">{{ __('There are no active job cards to work on right now.') }}</p>
					</div>
				</Transition>

				<!-- Raise Alarm -->
				<!-- <div class="raise-alarm-box mb-4 w-50 border border-dark rounded p-4" style="min-width: 650px;">
				<div class="d-flex flex-column justify-content-between mb-1 py-3">
					<div class="d-flex align-items-center">
						<span class="fa fa-exclamation-triangle mr-2"
							style="color:#ffc107; border:1px solid #ffc107; border-radius:50%; padding:4px;"></span>
						<h5 class="mb-1">{{ __('Raise Alarm') }}</h5>
					</div>
					<div class="text-muted small">
						{{ __('Report issues to the mixer operator') }}
					</div>
				</div>
				<button class="btn btn-outline-warning btn-block border border-warning" @click="openIssueDialog">
					<span class="fa fa-exclamation-triangle mr-1"></span>
					{{ __('Report Issue to Mixer') }}
				</button>
			</div> -->

				<!-- Downstream Alarms -->
				<!-- <div class="downstream-alarms-box w-50 border border-dark rounded p-4" style="min-width: 650px;">
				<div class="d-flex justify-content-between align-items-center mb-2">
					<div>
						<span class="fa fa-bell mr-1"></span>
						<span class="font-weight-bold">{{ __('Alarms') }}</span>
						<span class="badge badge-danger ml-2 alarms-count">{{ alarms.length }}</span>
					</div>
					<a href="javascript:void(0)" class="text-muted small" @click="toggleAlarms">
						<span class="fa fa-chevron-down"></span>
					</a>
				</div>
				<div class="alarms-list pt-4" v-show="showAlarms">
					<div v-for="(a, idx) in alarms" :key="idx" class="alarm-card mb-2"
						:style="`background:${a.tone === 'danger' ? '#ffecec' : '#fff9e6'};border-radius:8px;padding:12px 16px;`">
						<div class="d-flex justify-content-between mb-1">
							<div class="font-weight-bold">{{ a.station }}</div>
							<div class="text-muted small">{{ a.time }}</div>
						</div>
						<div class="text-uppercase text-muted small mb-1">{{ a.type }}</div>
						<div class="small">{{ a.description }}</div>
					</div>
				</div>
			</div> -->

				<!-- Simple modal for Raise Alarm -->
				<!-- <div v-if="issueDialogOpen" class="modal-backdrop fade show"></div>
			<div v-if="issueDialogOpen" class="modal d-block" tabindex="-1">
				<div class="modal-dialog">
					<div class="modal-content">
						<div class="modal-header">
							<h5 class="modal-title">{{ __('Raise Alarm') }}</h5>
							<button type="button" class="close" @click="issueDialogOpen = false">
								<span>&times;</span>
							</button>
						</div>
						<div class="modal-body">
							<div class="form-group">
								<label>{{ __('Issue Type') }}</label>
								<select class="form-control" v-model="issueType">
									<option>Quality Issue</option>
									<option>Machine Problem</option>
									<option>Material Issue</option>
									<option>Other</option>
								</select>
							</div>
							<div class="form-group">
								<label>{{ __('Description') }}</label>
								<textarea class="form-control" rows="3" v-model="issueDescription"></textarea>
							</div>
							<div class="form-group">
								<label>{{ __('Serial Number') }}</label>
								<input type="text" class="form-control" :value="serial" disabled />
							</div>
						</div>
						<div class="modal-footer">
							<button class="btn btn-secondary" @click="issueDialogOpen = false">
								{{ __('Cancel') }}
							</button>
							<button class="btn btn-primary" @click="submitIssue">
								{{ __('Submit') }}
							</button>
						</div>
					</div>
				</div>
			</div> -->
			</div>
		</div>
	</div>
</template>

<style scoped>
.queue-sidebar {
	background-color: var(--bg-light, #fcfcfc);
	border-color: var(--border-color) !important;
}

[data-theme="dark"] .queue-sidebar {
	background-color: var(--control-bg, #1f2124);
}

.empty-queue-state {
	background-color: var(--fg-color);
	border-style: dashed !important;
	border-color: var(--border-color) !important;
}

.item-time-badge {
	background-color: var(--control-bg);
	color: var(--text-color);
	border-color: var(--border-color) !important;
}

.slab-card {
	transition: all 0.2s ease;
	border-radius: 8px;
	background-color: var(--fg-color, #ffffff);
}

.slab-card:hover {
	transform: translateX(4px);
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
}

[data-theme="dark"] .slab-card {
	background-color: var(--card-bg, #242629);
	border: 1px solid var(--border-color) !important;
}

[data-theme="dark"] .slab-card:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
}

.active-card {
	box-shadow: 0 2px 8px rgba(0, 123, 255, 0.15) !important;
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

.active-job-card {
	background-color: #fafbfc;
	border: 1px solid var(--border-color);
	box-shadow: var(--shadow-base);
	transition: all 0.3s ease;
}

[data-theme="dark"] .active-job-card {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
	border-color: var(--border-color);
	background-color: #242629;
}

.badge-pill {
	padding: 0.5rem;
}

.repressed-badge {
	background-color: #fff3cd !important;
	color: #856404 !important;
	border: 1px solid #ffeeba;
}

[data-theme="dark"] .repressed-badge {
	background-color: #664d03 !important;
	color: #ffda6a !important;
	border: 1px solid #664d03;
}
</style>
