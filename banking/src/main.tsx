import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import './lib/namespace'


if (import.meta.env.DEV) {
  fetch('/api/method/erpnext.www.banking.get_context_for_dev', {
    method: 'POST',
  })
    .then(response => response.json())
    .then((values) => {
      const v = JSON.parse(values.message)
      if (!window.frappe) window.frappe = {};
      //@ts-expect-error - frappe will be available
      frappe.boot = v
      //@ts-expect-error - frappe will be available
      frappe._messages = frappe.boot["__messages"];
      //@ts-expect-error - frappe will be available
      frappe.model.sync(frappe.boot.docs);
      createRoot(document.getElementById('root') as HTMLElement).render(
        <StrictMode>
          <App />
        </StrictMode>,
      )

    })
} else {
  //@ts-expect-error - frappe will be available
  frappe.model.sync(frappe.boot.docs);
  createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
