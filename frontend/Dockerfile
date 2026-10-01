FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY public /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=10 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
