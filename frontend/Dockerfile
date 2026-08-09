FROM node:20-alpine

WORKDIR /app

# Install dependencies separately for better layer caching
COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
