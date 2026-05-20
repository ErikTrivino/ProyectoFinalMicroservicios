FROM node:22-alpine

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json ./

RUN pnpm install --prod --ignore-scripts

COPY . .

EXPOSE 80

CMD ["pnpm", "start"]
