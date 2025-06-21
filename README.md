# Analizador de logs 
Esta herramienta nos ayudará a analizar los logs y filtración de estos para poder trabajar con los datos del servidor de nuestra web, ayudándonos a saber que es lo que está ocurriendo de manera más exacta sin los problemas que podemos encontrarnos entre ellos de las aceptaciopnes de cookies.

## Estructura del Proyecto

```
ANALISIS-LOGS

├── src
│   ├── app.py                # Punto de entrada de la aplicación Streamlit
│   ├── components
│   │   ├── __init__.py       # Inicializa el paquete de componentes
│   │   ├── filters.py         # Funciones para filtrar logs
│   │   └── visualizations.py   # Funciones para visualizar logs
│   ├── data
│   │   ├── __init__.py       # Inicializa el paquete de datos
│   │   └── log_processor.py   # Lógica para procesar archivos de logs
│   └── utils
│       ├── __init__.py       # Inicializa el paquete de utilidades
│       └── file_handlers.py   # Funciones para manejar archivos
├── data
│   ├── raw                   # Directorio para archivos de logs sin procesar
│   └── processed             # Directorio para archivos de logs procesados
├── config
│   └── settings.py           # Configuración de la aplicación
├── requirements.txt          # Dependencias del proyecto
├── .streamlit
│   └── config.toml           # Configuración de Streamlit
└── README.md                 # Documentación del proyecto
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

## Contribuciones

Las contribuciones son bienvenidas. Si deseas contribuir, por favor abre un issue o envía un pull request.

## Licencia

Este proyecto está bajo la Licencia MIT.