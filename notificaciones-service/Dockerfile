FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# El puerto 8084 es el definido en los requisitos [cite: 181]
EXPOSE 8084
CMD ["npm", "start"]