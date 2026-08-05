#!/bin/sh
set -eu

preset="${APP_PRESET:-none}"

# >>> preset:laravel,legacy
write_php_config() {
  cat > /etc/nginx/conf.d/default.conf <<NGINX
server {
    listen 80;
    server_name _;
    root /workspace/apps/public;
    index index.php index.html;

    client_max_body_size 64m;

    location = /health {
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME \$document_root/index.php;
        fastcgi_param DOCUMENT_ROOT \$document_root;
        fastcgi_pass php:9000;
    }

    location / {
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    location ~ \\.php\$ {
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_param DOCUMENT_ROOT \$document_root;
        fastcgi_pass php:9000;
    }
}
NGINX
}
# <<< preset

# >>> preset:next
write_next_config() {
  cat > /etc/nginx/conf.d/default.conf <<'NGINX'
server {
    listen 80;
    server_name _;

    location = /health {
        proxy_pass http://node:3000/api/health;
    }

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_pass http://node:3000;
    }
}
NGINX
}
# <<< preset

write_placeholder_config() {
  cat > /etc/nginx/conf.d/default.conf <<'NGINX'
server {
    listen 80;
    server_name _;
    root /workspace/apps;
    index index.html;

    location = /health {
        add_header Content-Type text/plain;
        return 204;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
NGINX
}

case "$preset" in
# >>> preset:laravel
  laravel)
    write_php_config
    ;;
# <<< preset
# >>> preset:next
  next)
    write_next_config
    ;;
# <<< preset
# >>> preset:legacy
  legacy)
    write_php_config
    ;;
# <<< preset
  none|"")
    write_placeholder_config
    ;;
  *)
    echo "Unknown APP_PRESET '${preset}'." >&2
    exit 1
    ;;
esac

exec "$@"
