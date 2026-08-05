FROM node:26-alpine

RUN apk add --no-cache git

COPY .docker/node/start-node-preset /usr/local/bin/start-node-preset
RUN chmod +x /usr/local/bin/start-node-preset

WORKDIR /workspace
