app:
  name: "{{PROJECT_NAME}}"
  title: "{{PROJECT_TITLE}}"
  width: {{WIDTH}}
  height: {{HEIGHT}}
  min_size: [600, 400]
  max_size: [1920, 1080]
  resizable: true
  icon: "assets/icon.ico"
  singleton: false
  centered: true
  theme: light

  dev:
    enabled: true
    vite_port: 5173
    debug: true

logging:
  level: INFO
  console: true
  to_frontend: true
  file: ""
  max_lines: 1000

process:
  default_timeout: 300

business: {}
