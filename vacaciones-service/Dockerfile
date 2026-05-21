FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --omit=dev --ignore-scripts

COPY . .

EXPOSE 80

CMD ["npm", "start"]
