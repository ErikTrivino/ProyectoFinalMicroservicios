FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install --omit=dev

COPY . .

EXPOSE 80

CMD ["npm", "start"]
