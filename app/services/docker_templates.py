DOCKER_TEMPLATES = {
    "Static": """
services:
  httpd:
    image: httpd:latest
    networks:
      - caddy_net
    volumes:
      - "./data:/usr/local/apache2/htdocs/"
    labels:
      caddy: "{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 80}}}}"
    restart: always

  filebrowser:
    image: filebrowser/filebrowser:latest
    networks:
      - caddy_net
    labels:
      caddy: "fb-{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 80}}}}"
    volumes:
      - "./filebrowser_data/filebrowser.db:/database.db"
      - "./data:/srv"
    command: --database /database.db
    restart: always

networks:
  caddy_net:
    external: true
""",
    "PHP": """
services:
  php:
    image: php:8.2-apache
    networks:
      - caddy_net
    volumes:
      - "./data:/var/www/html/"
    labels:
      caddy: "{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 80}}}}"
    restart: always

  filebrowser:
    image: filebrowser/filebrowser:latest
    networks:
      - caddy_net
    labels:
      caddy: "fb-{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 80}}}}"
    volumes:
      - "./filebrowser_data/filebrowser.db:/database.db"
      - "./data:/srv"
    command: --database /database.db
    restart: always

networks:
  caddy_net:
    external: true
""",
    "Nodejs": """
services:
  app:
    image: node:18
    networks:
      - caddy_net
    working_dir: /usr/src/app
    volumes:
      - "./data:/usr/src/app"
    command: ["npm", "start"]
    labels:
      caddy: "{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 3000}}}}"
    restart: always

  filebrowser:
    image: filebrowser/filebrowser:latest
    networks:
      - caddy_net
    labels:
      caddy: "fb-{webname}.cloudfaster.app"
      caddy.reverse_proxy: "{{{{upstreams 80}}}}"
    volumes:
      - "./filebrowser_data/filebrowser.db:/database.db"
      - "./data:/srv"
    command: --database /database.db
    restart: always

networks:
  caddy_net:
    external: true
""",
    # Puedes agregar más plantillas aquí siguiendo el mismo patrón
}