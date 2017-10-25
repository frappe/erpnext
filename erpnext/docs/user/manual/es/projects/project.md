# Proyecto

El manejo de proyectos en ERPNext se hace a traves de tareas. Puedes crear un proyecto y asignar varias tareas al mismo.

<img class="screenshot" alt="Project" src="/docs/assets/img/project/project.png">

También puedes hacer el seguimiento del % completado del proyecto usando diferentes métodos.

  1. Tareas Completadas
  2. Progreso de tareas
  3. Peso de tarea

<img class="screenshot" alt="Project" src="/docs/assets/img/project/project-percent-complete.png">

Algunos ejemplos de como el % completado es cálculado basado en tareas.

<img class="screenshot" alt="Project" src="/docs/assets/img/project/percent-complete-calc.png">

<img class="screenshot" alt="Project" src="/docs/assets/img/project/percent-complete-formula.png">

### Manejando tareas

Los proyecto pueden ser divididos en multiples tareas.
Las tareas pueden ser creadas a traves del documento de Proyecto o pueden ser creadas via [Tarea](/docs/user/manual/en/projects/tasks.html)

<img class="screenshot" alt="Project" src="/docs/assets/img/project/project_task.png">

* Para ver las tareas creadas a un proyecto click en 'Tasks'

<img class="screenshot" alt="Project - View Task" src="/docs/assets/img/project/project_view_task.png">

<img class="screenshot" alt="Project - Task List" src="/docs/assets/img/project/project_task_list.png">

* También puedes ver las tareas desde la misma vista del proyecto.

<img class="screenshot" alt="Project - Task Grid" src="/docs/assets/img/project/project_task_grid.png">

* Para agregar peso a las tareas puedes seguir los pasos siguientes

<img class="screenshot" alt="Project - Task Grid" src="/docs/assets/img/project/tasks.png">
<img class="screenshot" alt="Project - Task Grid" src="/docs/assets/img/project/task-weights.png">


### Manejando tiempo

ERPNext usa [Time Log](/docs/user/manual/en/projects/time-log.html) para hacer el seguimiento del progreso de un Proyecto.
Puedes crear registros de tiempo sobre cada Tarea.
El tiempo actual de inicio y finalización junto con el costo deben ser actualizados basados en los Registros de Tiempo.

* Para ver los Registros de Tiempo realizados a un proyecto, dar click en 'Time Logs'

<img class="screenshot" alt="Project - View Time Log" src="/docs/assets/img/project/project_view_time_log.png">

<img class="screenshot" alt="Project - Time Log List" src="/docs/assets/img/project/project_time_log_list.png">

* Puedes agregar un registro de tiempo directamente y luego asociarlo con el proyecto.

<img class="screenshot" alt="Project - Link Time Log" src="/docs/assets/img/project/project_time_log_link.png">

### Gestión de gastos

Puede reservar la [Reclamación de gastos](/docs/user/manual/en/human-resources/expense-claim.html) contra una tarea de proyecto.
El sistema actualizará el monto total de las reclamaciones de gastos en la sección de costos del proyecto.

* Para ver las reclamaciones de gastos realizadas en un proyecto, haga clic en 'Reclamaciones de gastos'

<img class="screenshot" alt="Project - View Expense Claim" src="/docs/assets/img/project/project_view_expense_claim.png">

* También puede crear un Reclamo de gastos directamente y vincularlo al Proyecto.

<img class="screenshot" alt="Project - Link Expense Claim" src="/docs/assets/img/project/project_expense_claim_link.png">

* El monto total de los Reclamos de gastos reservados contra un proyecto se muestra en 'Reclamo de gastos totales' en la Sección de Costos del proyecto

<img class="screenshot" alt="Project - Total Expense Claim" src="/docs/assets/img/project/project_total_expense_claim.png">

### Centro de Costo

Puedes crear un [Cost Center](/docs/user/manual/en/accounts/setup/cost-center.html) sobre un proyecto o usar un centro de costo existente para hacer el seguimiento de todos los gastos realizados al proyecto.

<img class="screenshot" alt="Project - Cost Center" src="/docs/assets/img/project/project_cost_center.png">

###Costeo del proyecto

La sección Costeo del proyecto le ayuda a rastrear el tiempo y los gastos incurridos en relación con el proyecto.

<img class="screenshot" alt="Project - Costing" src="/docs/assets/img/project/project_costing.png">

* La sección de cálculo de costos se actualiza según los registros de tiempo realizados.

* El margen bruto es la diferencia entre el monto total de costos y el monto total de facturación

###Facturación

Puedes crear/enlazar una [Sales Order](/docs/user/manual/en/selling/sales-order.html) a un proyecto. Una vez asociada puedes usar el módulo de ventas para facturar a un cliente sobre el proyecto.

<img class="screenshot" alt="Project - Sales Order" src="/docs/assets/img/project/project_sales_order.png">

###Gantt Chart

Un Gantt Chart muestra la planificación del proyecto.
ERPNext te provee con una vista para visualizar las tareas de forma calendarizada usando un Gantt Chart (Hoja de Gantt).

* Para visualizar el gantt chart de un proyecto, ve hasta el proyecto y dar click en 'Gantt Chart'

<img class="screenshot" alt="Project - View Gantt Chart" src="/docs/assets/img/project/project_view_gantt_chart.png">

<img class="screenshot" alt="Project - Gantt Chart" src="/docs/assets/img/project/project_gantt_chart.png">

{next}
