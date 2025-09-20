# Étape 1 : Builder Angular
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build --prod

# Étape 2 : Nginx pour servir Angular et proxy vers FastAPI
FROM nginx:alpine
COPY --from=build /app/dist/frontend /usr/share/nginx/html

# Supprime la config par défaut
RUN rm /etc/nginx/conf.d/default.conf

# Ajoute notre config Nginx avec proxy vers backend
COPY nginx.conf /etc/nginx/conf.d/

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]