<script setup>
import { ref, computed, onMounted } from 'vue';

// core state
// const loading = ref(false);
const jobCard = ref(null);
const status = ref('Pending');
const serial = ref('SLB-2025-00427');
const colour = ref('Carrara White');
const timerHandle = ref(null);

const processStarted = ref(false);
const processStartTime = ref(null);
const processElapsed = ref(0);
const processTimerHandle = ref(null);
const processReady = ref(true);

const slabCreated = ref(false);
const slabNumber = ref(null);
const jobCardSubmitted = ref(false);
const preparedQty = ref(0);
const stockEntryName = ref('');
const transferredQty = ref(0);     
const transferSuccess = ref(false); 
const nextWorkOrder = ref(''); 
const bomNo = ref('Loading...');
const bomQty = ref(0);
const line = ref('L1'); 
const workstation = ref('');
const error = ref(null);              
const batchNo = ref(null);

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

// UI flags
const showStartButton = ref(true);
const showAlarms = ref(true);

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

// actions
onMounted(async () => {
    const route = frappe.get_route();
    const station = route[1] || props.process;
    jobCard.value = route[2] || props.job_card;

    if (!jobCard.value) {
        error.value = __('No Job Card found in route');
        return;
    }
    // await this.loadIncomingSlabs();
    // setInterval(() => this.loadIncomingSlabs(), 10000);

    try {
        const jc = await frappe.db.get_doc('Job Card', jobCard.value);
        if (jc.bom_no) {
            batchNo.value = jc.bom_no;  
        }
      
        jobCardSubmitted.value = jc.docstatus === 1 || jc.status === 'Completed';  
        if (jobCardSubmitted.value) {
            preparedQty.value = jc.total_completed_qty || jc.for_quantity || 0;
        }
        // createSlab();

        const stateRes = await frappe.call ({
          method: 'erpnext.manufacturing.page.operator_station.operator_station.get_operator_state',
          args: {
            job_card: jobCard.value,
            process_name: station
          }
        });
        const state = stateRes.message || {};
        processStarted.value = !!state[`${station}_started`];
        processStartTime.value = state[`${station}_start_time`];

        jobCardSubmitted.value = !!state.job_card_submitted || false;  
        if (jobCardSubmitted.value) {
            stockEntryName.value = state.stock_entry_name || '';
        }

        if (processStarted.value && processStartTime.value) {
            const start = frappe.datetime.str_to_obj(processStartTime.value);
            const now = frappe.datetime.now_datetime();
            const diffSeconds = (new Date(now) - new Date(start)) / 1000;
            processElapsed.value = Math.max(0, Math.floor(diffSeconds));

            if (processTimerHandle.value) clearInterval(processTimerHandle.value);
            processTimerHandle.value = setInterval(() => {
                processElapsed.value += 1;
            }, 1000);
        } 
        else {
            processElapsed.value = 0;
            if (processTimerHandle.value) {
                clearInterval(processTimerHandle.value);
                processTimerHandle.value = null;
            }
        }
    } 
    catch (e) {
        error.value = e.message || e;
        frappe.msgprint(__('Failed to load BOM ingredients: {0}', [error.value]));
    } 
});

// async loadIncomingSlabs() {
//   this.loading = true;
//   const response = await frappe.call({
//     method: 'erpnext.manufacturing.page.operator_station.operator_station.loadIncomingSlabs',
//     args: {

//     }
//   })
// }


async function createSlab() {
  if (!jobCard.value || slabCreated.value) return
  
  try {
    const result = await frappe.call({
      method: "erpnext.manufacturing.utils.slab.create_slab",
      args: { 
        line: line.value || 'L1',
        job_card: jobCard.value.name,
        workstation: workstation.value
      }
    })
    
    slabCreated.value = true
    slabNumber.value = result;
    const jc = await frappe.db.get_doc('Job Card', jobCard.value);
    if (jc) {
      bomNo.value = jc.bom_no;  
    }
  } catch (e) {
    frappe.msgprint(__('Slab creation failed: {0}', [e.message]))
  }
}

// async loadIncomingSlabs() {
//   this.loading = true;
//   const response = await frappe.call({
//     method: "frappe.client.get_list",
//     args: {
//       doctype: "Serial No",
//       filters: {
//         item_code: "KY-1005 (3 CM) - FG",  // or dynamic
//         warehouse: "Mixing-FG - SPL",      // previous station FG
//         status: "Active"                   // available slabs
//       },
//       fields: ["name as serial", "item_code", "warehouse"]
//     }
//   });
  
  // Enrich with dimensions/status
//   this.incomingSlabs = await Promise.all(
//     response.message.map(async slab => ({
//       serial: slab.serial,
//       subtitle: await this.getSlabDimensions(slab.serial)  // custom method
//     }))
//   );
//   this.loading = false;
// }


async function startOperation() {
  const route = frappe.get_route();
    const station = route[1] || props.process;
    jobCard.value = route[2] || props.job_card;
    frappe.confirm(
        __('Start Distribution now?'),
        async () => {
            try {
                await frappe.call({
                    method: 'erpnext.manufacturing.page.operator_station.operator_station.start_distribution',
                    args: { 
                      job_card: jobCard.value,
                      process_name: station
                     }
                });
                status.value = 'In Progress';
                showStartButton.value = false;
                processStarted.value = true;
                processStartTime.value = frappe.datetime.now_datetime();

                processElapsed.value = 0;
                if (processTimerHandle.value) {
                    clearInterval(processTimerHandle.value);
                }
                processTimerHandle.value = setInterval(() => {
                    processElapsed.value += 1;
                }, 1000);
    
                frappe.msgprint(__('Process started'));
            }
            catch (e) {
                frappe.msgprint(__('Failed to start Job Card: {0}', [e.message || e]));
            }
        },
        () => {
            frappe.msgprint(__('Process was not started.'));
        }
    );
}

async function finishOperation() {
  const route = frappe.get_route();
  const station = route[1] || props.process;
  jobCard.value = route[2] || props.job_card;
  if (processTimerHandle.value) {
      clearInterval(processTimerHandle.value);
      processTimerHandle.value = null;
  }
    try {
        const result = await frappe.call({
            method: 'erpnext.manufacturing.page.operator_station.operator_station.finish_distribution',
            args: {
                job_card: jobCard.value,
                process_name: station
            },
        });
        status.value = 'Finished';
        processStarted.value = false;
        processStartTime.value = null;
        processElapsed.value = 0;
        processReady.value = false;

        jobCardSubmitted.value = true;
        preparedQty.value = result.message.job_card_qty;
        stockEntryName.value = result.message.stock_entry;
        bomQty.value = result.message.bom_qty || 0;
        nextWorkOrder.value = result.message.next_work_order || '';
        transferredQty.value = 0;
        transferSuccess.value = false;

        frappe.msgprint(result.message.message);    
        if (result.message.work_order_status === 'Completed') {
            frappe.show_alert({
                message: __('Work Order also Completed!'),
                indicator: 'green'
            });
        }
        transferToFGWarehouse();
    }

    catch (error) {
        console.error('error.message:', error.message);
        const errorMsg = error.message || 
                        (error._server_messages?.[0]?.message) || 
                        JSON.stringify(error);
        
        frappe.msgprint({ 
            title: __('Error'),
            indicator: 'red',
            message: `Failed to complete Job Card:<br><pre>${errorMsg}</pre>`
        });
    }
}

async function transferToFGWarehouse() {
  try {
    const jc = await frappe.db.get_doc('Job Card', jobCard.value);
    const workOrder = jc.work_order; 
    
    if (!workOrder) {
        frappe.msgprint(__('Work Order required from Job Card'));
        return;
    }

    const result = await frappe.call({
        method: 'erpnext.manufacturing.page.operator_station.operator_station.transfer_to_next_process',
        args: {
            current_work_order: workOrder,  
            qty: bomQty.value
        },
        freeze: true,
        freeze_message: __('Transferring to Distribution')
    });
    
    transferredQty.value += result.message.qty_transferred;   
    frappe.msgprint({
        title: __('Transfer Complete'),
        message: result.message.message,
        indicator: 'green'
    });
    
    frappe.show_alert({
        message: `Next: ${result.message.next_work_order}`,
        indicator: 'blue'
    });
  } 
  catch (error) {
      frappe.msgprint(__('Transfer failed: {0}', [error.message]));
  }
}

async function loadBomQty() {
  try {
    const jc = await frappe.db.get_doc('Job Card', jobCard.value);
    const result = await frappe.call({
        method: 'erpnext.manufacturing.page.operator_station.operator_station.get_next_process_bom_qty',
        args: { current_work_order: jc.work_order }
    });
    
    bomQty.value = result.message.bom_qty; 
    nextWorkOrder.value = result.message.next_work_order;
  } 
  catch (error) {
      console.error('BOM qty load failed:', error);
      bomQty.value = 0;
  }
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
      status.value = 'Discarded';
      stopAndResetTimer();
      showTimer.value = false;
      showActions.value = false;
      showStartButton.value = true;
      frappe.msgprint(__('Job is discarded'));
    }
  );
}

function toggleAlarms() {
  showAlarms.value = !showAlarms.value;
}

function openIssueDialog() {
  issueDialogOpen.value = true;
}

function submitIssue() {
  const now = frappe.datetime.now_time();
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
    return 'background:#d4f8d4;color:#137a13;padding:.5rem';
  }
  if (status.value === 'Finished') {
    return 'background:#d1ecf1;color:#0c5460;padding:.5rem';
  }
  if (status.value === 'Halted') {
    return 'background:#ffeeba;color:#856404;padding:.5rem';
  }
  if (status.value === 'Discarded') {
    return 'background:#f8d7da;color:#721c24;padding:.5rem';
  }
  return 'background:#e9ecef;color:#6c757d;padding:.5rem';
}
</script>

<template>
  <div class="operator-station page-card d-flex flex-column align-items-center">
    <!-- Current Job Card -->
    <div class="current-job-card mb-4 border border-dark w-50 rounded p-4">
      <div class="status text-center mb-2" style="font-size:1rem">
        <span class="badge badge-pill" :style="statusStyle()">
          {{ __(status) }}
        </span>
      </div>

      <div class="text-center text-muted small">{{ __('SERIAL NUMBER') }}</div>
      <h2 class="job-serial text-center font-weight-bold mb-2 p-3">
        {{ serial }}
      </h2>

      <div class="text-center text-muted small mb-1">{{ __('Colour') }}</div>
      <div class="d-flex justify-content-center align-items-center mb-3">
        <span class="job-color mr-2">{{ colour }}</span>
        <span class="color-swatch"
              style="width:24px;height:24px;border-radius:4px;background:#f5f5f5;border:1px solid #ddd;"></span>
      </div>     

      <div class="text-center mb-2" v-if="processReady">
        <button class="btn btn-success py-3 px-4" @click="startOperation">
          <span class="fa fa-play mr-1 pr-2"></span>{{ __('Start Job') }}
        </button>
      </div>

      <div class="text-center mb-3" v-if="processStarted && !jobCardSubmitted">
        <div class="text-success" style="font-size:1.5rem">
          <span class="fa fa-clock-o mr-1"></span>
          <span class="job-timer">{{ formattedTime }}</span>
        </div>
      </div>

      <div class="text-center mb-2" v-if="processStarted">
        <button class="btn btn-info mr-2" @click="finishOperation">
          <span class="fa fa-check-square-o mr-1"></span>{{ __('Finish Job') }}
        </button>
        <button class="btn btn-warning mr-2" @click="haltJob">
          <span class="fa fa-pause-circle-o mr-1"></span>{{ __('Halt Job') }}
        </button>
        <button class="btn btn-danger" @click="discardJob">
          <span class="fa fa-trash-o mr-1"></span>{{ __('Discard') }}
        </button>
      </div>
    </div>

    <!-- Raise Alarm -->
    <div class="raise-alarm-box mb-4 w-50 border border-dark rounded p-4">
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
      <button class="btn btn-outline-warning btn-block border border-warning"
              @click="openIssueDialog">
        <span class="fa fa-exclamation-triangle mr-1"></span>
        {{ __('Report Issue to Mixer') }}
      </button>
    </div>

    <!-- Downstream Alarms -->
    <div class="downstream-alarms-box w-50 border border-dark rounded p-4">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div>
          <span class="fa fa-bell mr-1"></span>
          <span class="font-weight-bold">{{ __('Downstream Alarms') }}</span>
          <span class="badge badge-danger ml-2 alarms-count">{{ alarms.length }}</span>
        </div>
        <a href="javascript:void(0)" class="text-muted small" @click="toggleAlarms">
          <span class="fa fa-chevron-down"></span>
        </a>
      </div>
      <div class="alarms-list pt-4" v-show="showAlarms">
        <div v-for="(a, idx) in alarms" :key="idx"
             class="alarm-card mb-2"
             :style="`background:${a.tone === 'danger' ? '#ffecec' : '#fff9e6'};border-radius:8px;padding:12px 16px;`">
          <div class="d-flex justify-content-between mb-1">
            <div class="font-weight-bold">{{ a.station }}</div>
            <div class="text-muted small">{{ a.time }}</div>
          </div>
          <div class="text-uppercase text-muted small mb-1">{{ a.type }}</div>
          <div class="small">{{ a.description }}</div>
        </div>
      </div>
    </div>

    <!-- Simple modal for Raise Alarm -->
    <div v-if="issueDialogOpen" class="modal-backdrop fade show"></div>
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
    </div>

  </div>
</template>
