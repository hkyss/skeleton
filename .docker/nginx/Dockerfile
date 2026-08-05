FROM nginx:1.31-alpine

COPY .docker/nginx/entrypoint.sh /usr/local/bin/project-gateway-entrypoint
RUN chmod +x /usr/local/bin/project-gateway-entrypoint

ENTRYPOINT ["project-gateway-entrypoint"]
CMD ["nginx", "-g", "daemon off;"]
