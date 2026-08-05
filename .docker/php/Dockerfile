FROM php:8.5-fpm-alpine

RUN apk add --no-cache \
    bash \
    curl \
    git \
    icu-dev \
    libzip-dev \
    unzip \
  && docker-php-ext-install intl pdo_mysql zip

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
COPY .docker/php/start-queue-preset /usr/local/bin/start-queue-preset

RUN chmod +x /usr/local/bin/start-queue-preset

WORKDIR /workspace
