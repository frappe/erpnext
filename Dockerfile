# ========= Dockerfile =========
FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    git curl mariadb-client redis-server build-essential nodejs npm \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY . /app/



RUN git clone --branch version-15 --depth 1 https://github.com/frappe/frappe.git /opt/frappe


RUN git clone --branch version-15 --depth 1 https://github.com/frappe/erpnext.git /opt/erpnext


RUN pip install --no-cache-dir -e /opt/frappe
RUN pip install --no-cache-dir -e /opt/erpnext


RUN pip install --no-cache-dir -r requirements.txt || true


RUN if [ -f package.json ]; then npm install && npm run build || true; fi


ENV PYTHONPATH=/app:/opt/frappe:/opt/erpnext
ENV PORT=8000


EXPOSE 8000


CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"]

