FROM frappe/erpnext:v16.8.2

# Copy the rebranded erpnext app source over the stock one
COPY --chown=frappe:frappe ./erpnext /home/frappe/frappe-bench/apps/erpnext/erpnext

# Copy updated root config files
COPY --chown=frappe:frappe ./package.json /home/frappe/frappe-bench/apps/erpnext/package.json
COPY --chown=frappe:frappe ./pyproject.toml /home/frappe/frappe-bench/apps/erpnext/pyproject.toml

# Install yarn deps and rebuild frontend assets
USER frappe
WORKDIR /home/frappe/frappe-bench
RUN bench build --app erpnext 2>/dev/null || \
    (cd apps/erpnext && yarn install --frozen-lockfile 2>/dev/null; cd /home/frappe/frappe-bench && bench build --app erpnext)
