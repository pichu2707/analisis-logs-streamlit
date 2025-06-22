# Analizador de Logs

Esta herramienta nos ayudará a analizar y filtrar logs para poder trabajar con los datos del servidor de nuestra web. Su propósito es entender con mayor precisión lo que está ocurriendo, evitando interferencias comunes como las aceptaciones de cookies.

## 📁 Estructura del Proyecto


```
ANALISIS-LOGS
.
├── logs.py
├── main.py
├── requirements.txt
├── streamlit_app.py
└── transform_logs.py
```

## Instalación

1. Clona el repositorio:
   ```
   git clone <URL_DEL_REPOSITORIO>
   cd snalisis-logs
   ```

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

## Uso

Para ejecutar la aplicación, utiliza el siguiente comando:

```
streamlit run streamlit_app.py
```

Una vez que la aplicación esté en funcionamiento, podrás cargar archivos de logs, aplicar filtros y visualizar los datos de manera interactiva.

## Formato de logs compatibles
Ahora mismo la herramietna está preparada para trabajar los siguientes formatos de log

2025-05-26T02:12:22+02:00 {code="200", domain="www.dominio.com", port="443"} {
  "agent": "Mozilla/5.0 (...)",
  "code": 200,
  "domain": "www.dominio.com",
  "forwardedfor": "00.00.000.00",
  "host": "00.00.000.00",
  "method": "GET",
  "path": "/public/486x243/imagen.jpg",
  "port": 443,
  ...
}


## Contribuciones

Las contribuciones son bienvenidas. Si deseas contribuir, por favor abre un issue o envía un pull request.

## Licencia

Este proyecto está bajo la Licencia MIT.