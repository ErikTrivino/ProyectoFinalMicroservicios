FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN pnpm install --prod --ignore-scripts

COPY . .

EXPOSE 80

CMD ["npm", "start"]
