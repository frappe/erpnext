# Tareas

Proyecto es dividido en Tareas.
En ERPNext, puedes crear las tareas de forma independiente.

<img class="screenshot" alt="Task" src="/docs/assets/img/project/task.png">

### Estado de una Tarea

Una tarea puede tener uno de los siguientes estados - Abierto, Trabajando, Pendiente de Revisión, Cerrado, o Cancelado.

<img class="screenshot" alt="Task - Status" src="/docs/assets/img/project/task_status.png">

* Por defecto, cada nueva tarea creada se le establece el estado 'Abierto'.

* Si un registro de tiempo es realizado sobre una tarea, su estado es asignado a 'Working'.

### Tarea Dependiente

Puedes especificar una lista de tareas dependientes en la sección 'Depende de'

<img class="screenshot" alt="Depends On" src="/docs/assets/img/project/task_depends_on.png">

* No puedes cerrar una tarea padre hasta que todas las tareas dependientes esten cerradas.

* Si una tarea dependiente se encuentra en retraso y se sobrepone con la fecha esperada de inicio de la tarea padre, el sistema va a re calandarizar la tarea padre.

### Manejando el tiempo

ERPNext usa [Time Log](/docs/user/manual/en/projects/time-log.html) para seguir el progreso de una tarea.
Puedes crear varios registros de tiempo para cada tarea.
El tiempo de inicio y fin actual junto con el costo es actualizado en base al Registro de Tiempo.

* Para ver el Registro de tiempo realizado a una tarea, dar click en 'Time Logs'

<img class="screenshot" alt="Task - View Time Log" src="/docs/assets/img/project/task_view_time_log.png">

<img class="screenshot" alt="Task - Time Log List" src="/docs/assets/img/project/task_time_log_list.png">

* Puedes también crear un Registro de Tiempo directamente y luego asociarlo a una Tarea.

<img class="screenshot" alt="Task - Link Time Log" src="/docs/assets/img/project/task_time_log_link.png">

### Gestión de gastos

Puede reservar la [Reclamación de gastos](/docs/user/manual/en/human-resources/expense-claim.html) contra una tarea de proyecto.
El sistema actualizará el monto total de las reclamaciones de gastos en la sección de costos del proyecto.

* Para ver las reclamaciones de gastos realizadas en un proyecto, haga clic en 'Reclamaciones de gastos'

<img class="screenshot" alt="Task - View Expense Claim" src="/docs/assets/img/project/task_view_expense_claim.png">

* También puede crear un Reclamo de gastos directamente y vincularlo al Proyecto.

<img class="screenshot" alt="Task - Link Expense Claim" src="/docs/assets/img/project/task_expense_claim_link.png">

* El monto total de los Reclamos de gastos reservados contra un proyecto se muestra en 'Reclamo de gastos totales' en la Sección de Costos del proyecto

<img class="screenshot" alt="Task - Total Expense Claim" src="/docs/assets/img/project/task_total_expense_claim.png">

{next}
