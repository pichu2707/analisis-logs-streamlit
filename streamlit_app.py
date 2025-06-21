import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from transform_logs import (
    crear_dataframe, crear_dataframe_sample, get_log_stats,
    filter_bots, create_sessions, get_session_stats
)
import os
from datetime import datetime, timedelta
import gc

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Logs",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Funciones auxiliares
@st.cache_data(show_spinner=False)
def load_data(archivo, modo_carga, max_lines=None, sample_size=50000):
    """Carga los datos con cache para mejor rendimiento"""
    if modo_carga == "Muestra aleatoria":
        return crear_dataframe_sample(archivo, sample_size)
    else:
        return crear_dataframe(archivo, max_lines)

def format_bytes(bytes_value):
    """Formatea bytes a formato legible"""
    if pd.isna(bytes_value) or bytes_value == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def get_file_info(archivo):
    """Obtiene información del archivo de manera más eficiente"""
    try:
        size = os.path.getsize(archivo)
        
        if size > 100 * 1024 * 1024:  # Si es mayor a 100MB
            with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
                sample_bytes = f.read(10000)  # Leer primeros 10KB
                lines_in_sample = sample_bytes.count('\n')
                
            if lines_in_sample > 0:
                estimated_lines = int((size / 10000) * lines_in_sample)
            else:
                estimated_lines = size // 100
        else:
            with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
                estimated_lines = sum(1 for _ in f)
                
        return size, max(1, estimated_lines)
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return 0, 1

def comparar_periodos(df, fecha1_inicio, fecha1_fin, fecha2_inicio, fecha2_fin, 
                     exclude_bots=True, use_sessions=False, session_timeout=30):
    """
    Compara dos períodos de tiempo y retorna estadísticas comparativas
    Incluye opciones para filtrar bots y analizar por sesiones
    """
    # Convertir fechas a datetime para comparación
    fecha1_inicio = pd.to_datetime(fecha1_inicio)
    fecha1_fin = pd.to_datetime(fecha1_fin)
    fecha2_inicio = pd.to_datetime(fecha2_inicio)
    fecha2_fin = pd.to_datetime(fecha2_fin)
    
    # Filtrar datos por períodos
    df_periodo1 = df[
        (pd.to_datetime(df['date']) >= fecha1_inicio) &
        (pd.to_datetime(df['date']) <= fecha1_fin)
    ]
    
    df_periodo2 = df[
        (pd.to_datetime(df['date']) >= fecha2_inicio) &
        (pd.to_datetime(df['date']) <= fecha2_fin)
    ]
    
    # Filtrar bots si está habilitado
    bots_filtrados_p1 = 0
    bots_filtrados_p2 = 0
    
    if exclude_bots:
        df_periodo1, bots_filtrados_p1 = filter_bots(df_periodo1, exclude_bots=True)
        df_periodo2, bots_filtrados_p2 = filter_bots(df_periodo2, exclude_bots=True)
    
    # Crear sesiones si está habilitado
    sessions_stats1 = {}
    sessions_stats2 = {}
    
    if use_sessions:
        df_periodo1 = create_sessions(df_periodo1, session_timeout_minutes=session_timeout)
        df_periodo2 = create_sessions(df_periodo2, session_timeout_minutes=session_timeout)
        
        sessions_stats1 = get_session_stats(df_periodo1)
        sessions_stats2 = get_session_stats(df_periodo2)
    
    # Calcular estadísticas para cada período
    if use_sessions and sessions_stats1 and sessions_stats2:
        requests1 = sessions_stats1.get('total_sessions', 0)
        requests2 = sessions_stats2.get('total_sessions', 0)
        ips1 = sessions_stats1.get('unique_users', 0)
        ips2 = sessions_stats2.get('unique_users', 0)
    else:
        stats1 = get_log_stats(df_periodo1)
        stats2 = get_log_stats(df_periodo2)
        requests1 = stats1.get('total_requests', 0)
        requests2 = stats2.get('total_requests', 0)
        ips1 = stats1.get('unique_ips', 0)
        ips2 = stats2.get('unique_ips', 0)
    
    # Calcular estadísticas tradicionales para errores y tamaño
    stats1 = get_log_stats(df_periodo1)
    stats2 = get_log_stats(df_periodo2)
    
    # Calcular diferencias y porcentajes
    diff_requests = requests2 - requests1
    pct_change_requests = ((requests2 - requests1) / requests1 * 100) if requests1 > 0 else 0
    
    diff_ips = ips2 - ips1
    pct_change_ips = ((ips2 - ips1) / ips1 * 100) if ips1 > 0 else 0
    
    errors1 = stats1.get('errors', 0)
    errors2 = stats2.get('errors', 0)
    diff_errors = errors2 - errors1
    pct_change_errors = ((errors2 - errors1) / errors1 * 100) if errors1 > 0 else 0
    
    size1 = stats1.get('total_size', 0)
    size2 = stats2.get('total_size', 0)
    diff_size = size2 - size1
    pct_change_size = ((size2 - size1) / size1 * 100) if size1 > 0 else 0
    
    comparacion = {
        'periodo1': {
            'inicio': fecha1_inicio.date(),
            'fin': fecha1_fin.date(),
            'requests': requests1,
            'ips': ips1,
            'errors': errors1,
            'size': size1,
            'stats': stats1,
            'bots_filtrados': bots_filtrados_p1,
            'sessions_stats': sessions_stats1
        },
        'periodo2': {
            'inicio': fecha2_inicio.date(),
            'fin': fecha2_fin.date(),
            'requests': requests2,
            'ips': ips2,
            'errors': errors2,
            'size': size2,
            'stats': stats2,
            'bots_filtrados': bots_filtrados_p2,
            'sessions_stats': sessions_stats2
        },
        'diferencias': {
            'requests': {'absoluta': diff_requests, 'porcentual': pct_change_requests},
            'ips': {'absoluta': diff_ips, 'porcentual': pct_change_ips},
            'errors': {'absoluta': diff_errors, 'porcentual': pct_change_errors},
            'size': {'absoluta': diff_size, 'porcentual': pct_change_size}
        },
        'dataframes': {
            'periodo1': df_periodo1,
            'periodo2': df_periodo2
        },
        'configuracion': {
            'exclude_bots': exclude_bots,
            'use_sessions': use_sessions,
            'session_timeout': session_timeout
        }
    }
    
    return comparacion

# Inicializar session state si no existe
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'archivo_actual' not in st.session_state:
    st.session_state.archivo_actual = None

# Título principal
st.title("📊 Análisis de Logs de Acceso")

# Crear tabs para organizar el contenido
tab1, tab2 = st.tabs(["📈 Análisis General", "📊 Comparativa de Fechas"])

with tab1:
    st.markdown("---")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Selección de archivo
    archivos_disponibles = [f for f in os.listdir('.') if f.endswith('.log')]
    if archivos_disponibles:
        archivo_seleccionado = st.sidebar.selectbox(
            "Selecciona archivo de log:",
            archivos_disponibles,
            index=0 if "uniite-travel-access.log" in archivos_disponibles else 0
        )
        
        # Mostrar información del archivo
        with st.spinner("Analizando archivo..."):
            file_size, estimated_lines = get_file_info(archivo_seleccionado)
        
        st.sidebar.markdown(f"**Tamaño:** {format_bytes(file_size)}")
        st.sidebar.markdown(f"**Líneas estimadas:** {estimated_lines:,}")
        
    else:
        st.error("No se encontraron archivos .log en el directorio")
        st.stop()
    
    # Modo de carga para archivos grandes
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Modo de Carga")
    
    if file_size > 100 * 1024 * 1024:  # Si es mayor a 100MB
        st.sidebar.warning("⚠️ Archivo grande detectado")
        modo_carga = st.sidebar.radio(
            "Selecciona modo de carga:",
            ["Muestra aleatoria", "Primeras líneas"],
            help="Para archivos grandes, recomendamos usar muestra aleatoria"
        )
    else:
        modo_carga = "Primeras líneas"
    
    # Configuración según el modo
    if modo_carga == "Muestra aleatoria":
        sample_size = st.sidebar.number_input(
            "Tamaño de muestra:",
            min_value=1000,
            max_value=1000000,
            value=min(50000, max(1000, estimated_lines)),
            step=5000,
            help="Número de líneas aleatorias a procesar"
        )
        max_lines = None
    else:
        default_value = min(50000, max(1000, estimated_lines))
        max_value = max(1000000, estimated_lines)
        
        max_lines = st.sidebar.number_input(
            "Máximo de líneas a procesar:",
            min_value=1000,
            max_value=max_value,
            value=default_value,
            step=5000,
            help=f"Máximo {estimated_lines:,} líneas disponibles"
        )
        sample_size = None
    
    # Botón para cargar datos
    cargar_datos = st.sidebar.button("🔄 Cargar/Actualizar Datos")
    
    # Verificar si necesita cargar datos
    necesita_cargar = (
        cargar_datos or 
        st.session_state.archivo_actual != archivo_seleccionado or 
        st.session_state.df.empty
    )
    
    if necesita_cargar:
        st.cache_data.clear()
        gc.collect()
        
        # Cargar datos con barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            with st.spinner("Cargando datos..."):
                status_text.text("Procesando archivo...")
                progress_bar.progress(0.1)
                
                if modo_carga == "Muestra aleatoria":
                    df, errores = load_data(archivo_seleccionado, modo_carga, sample_size=sample_size)
                else:
                    df, errores = load_data(archivo_seleccionado, modo_carga, max_lines=max_lines)
                
                # Guardar en session state
                st.session_state.df = df
                st.session_state.archivo_actual = archivo_seleccionado
                st.session_state.errores = errores
                
                progress_bar.progress(1.0)
                status_text.text("¡Datos cargados exitosamente!")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")
            st.error("Intenta reducir el tamaño de muestra o usar modo 'Muestra aleatoria'")
            st.stop()
        
        # Limpiar barra de progreso
        progress_bar.empty()
        status_text.empty()
    
    # Usar datos del session state
    df = st.session_state.df
    errores = getattr(st.session_state, 'errores', 0)
    
    if df.empty:
        st.error("No se pudieron cargar datos del archivo seleccionado")
        st.stop()
    
    # Obtener estadísticas
    try:
        stats = get_log_stats(df)
    except Exception as e:
        st.error(f"Error al calcular estadísticas: {e}")
        stats = {}
    
    # Información general
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Información General")
    
    if stats:
        st.sidebar.metric("Total de requests", f"{stats.get('total_requests', 0):,}")
        st.sidebar.metric("IPs únicas", f"{stats.get('unique_ips', 0):,}")
        st.sidebar.metric("Errores en parsing", errores)
        
        if stats.get('total_size', 0) > 0:
            st.sidebar.metric("Datos transferidos", format_bytes(stats['total_size']))
    
    # Mostrar información del modo de carga
    if modo_carga == "Muestra aleatoria":
        st.sidebar.info(f"📊 Mostrando muestra aleatoria de {len(df):,} registros")
    else:
        st.sidebar.info(f"📊 Mostrando primeros {len(df):,} registros")
    
    # Análisis general
    st.subheader("📊 Resumen General")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Requests", f"{len(df):,}")
    with col2:
        st.metric("IPs Únicas", f"{df['ip'].nunique():,}")
    with col3:
        errores_total = len(df[df['status_code'] >= 400]) if 'status_code' in df.columns else 0
        st.metric("Errores (4xx/5xx)", f"{errores_total:,}")
    with col4:
        if 'size' in df.columns:
            st.metric("Datos Transferidos", format_bytes(df['size'].sum()))

with tab2:
    st.markdown("---")
    st.header("📊 Comparativa entre Períodos")
    
    if st.session_state.df.empty:
        st.warning("Primero debes cargar datos en la pestaña 'Análisis General'")
    else:
        df = st.session_state.df  # Usar datos del session state
        
        # Configuraciones de análisis
        st.markdown("### ⚙️ Configuración del Análisis")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            exclude_bots = st.checkbox(
                "🤖 Excluir bots y crawlers",
                value=True,
                help="Filtra tráfico de Google, Bing, Yandex y otros bots para mostrar solo tráfico humano real"
            )
            
            if exclude_bots:
                st.info("✅ Se filtrarán bots como Googlebot, Bingbot, Yandexbot, etc.")
        
        with col_config2:
            use_sessions = st.checkbox(
                "👥 Analizar por sesiones",
                value=False,
                help="Agrupa requests por IP y tiempo para simular sesiones de usuario como en GA4"
            )
            
            if use_sessions:
                session_timeout = st.slider(
                    "Timeout de sesión (minutos):",
                    min_value=10,
                    max_value=120,
                    value=30,
                    help="Tiempo sin actividad para considerar una nueva sesión"
                )
                st.info(f"✅ Sesiones con timeout de {session_timeout} minutos")
            else:
                session_timeout = 30
        
        # Obtener rango de fechas disponibles
        try:
            fecha_min = pd.to_datetime(df['date']).min().date()
            fecha_max = pd.to_datetime(df['date']).max().date()
            
            st.info(f"📅 Datos disponibles desde {fecha_min} hasta {fecha_max}")
            
            # Configuración de períodos
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔵 Período 1")
                periodo1_inicio = st.date_input(
                    "Fecha inicio período 1:",
                    value=fecha_min,
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="p1_inicio"
                )
                periodo1_fin = st.date_input(
                    "Fecha fin período 1:",
                    value=fecha_min + timedelta(days=7),
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="p1_fin"
                )
            
            with col2:
                st.subheader("🔴 Período 2")
                periodo2_inicio = st.date_input(
                    "Fecha inicio período 2:",
                    value=fecha_max - timedelta(days=7),
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="p2_inicio"
                )
                periodo2_fin = st.date_input(
                    "Fecha fin período 2:",
                    value=fecha_max,
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="p2_fin"
                )
            
            # Validar fechas
            if periodo1_inicio > periodo1_fin:
                st.error("❌ La fecha de inicio del período 1 debe ser anterior a la fecha de fin")
            elif periodo2_inicio > periodo2_fin:
                st.error("❌ La fecha de inicio del período 2 debe ser anterior a la fecha de fin")
            else:
                # Realizar comparación
                if st.button("🔍 Realizar Comparación", type="primary"):
                    with st.spinner("Realizando comparación..."):
                        comparacion = comparar_periodos(
                            df, periodo1_inicio, periodo1_fin,
                            periodo2_inicio, periodo2_fin,
                            exclude_bots=exclude_bots,
                            use_sessions=use_sessions,
                            session_timeout=session_timeout
                        )
                    
                    # Mostrar configuración aplicada
                    st.markdown("---")
                    config_info = []
                    if exclude_bots:
                        config_info.append(f"🤖 Bots excluidos: {comparacion['periodo1']['bots_filtrados'] + comparacion['periodo2']['bots_filtrados']:,}")
                    if use_sessions:
                        config_info.append(f"👥 Análisis por sesiones (timeout: {session_timeout}min)")
                    else:
                        config_info.append("📄 Análisis por requests individuales")
                    
                    st.info(" | ".join(config_info))
                    
                    # Mostrar resultados
                    st.subheader("📊 Resultados de la Comparación")
                    
                    # Métricas principales
                    col1, col2, col3, col4 = st.columns(4)
                    
                    metric_label = "Total Sesiones" if use_sessions else "Total Requests"
                    users_label = "Usuarios Únicos" if use_sessions else "IPs Únicas"
                    
                    with col1:
                        diff_requests = comparacion['diferencias']['requests']
                        st.metric(
                            metric_label,
                            f"{comparacion['periodo2']['requests']:,}",
                            delta=f"{diff_requests['absoluta']:+,} ({diff_requests['porcentual']:+.1f}%)"
                        )
                    
                    with col2:
                        diff_ips = comparacion['diferencias']['ips']
                        st.metric(
                            users_label,
                            f"{comparacion['periodo2']['ips']:,}",
                            delta=f"{diff_ips['absoluta']:+,} ({diff_ips['porcentual']:+.1f}%)"
                        )
                    
                    with col3:
                        diff_errors = comparacion['diferencias']['errors']
                        st.metric(
                            "Errores (4xx/5xx)",
                            f"{comparacion['periodo2']['errors']:,}",
                            delta=f"{diff_errors['absoluta']:+,} ({diff_errors['porcentual']:+.1f}%)"
                        )
                    
                    with col4:
                        diff_size = comparacion['diferencias']['size']
                        st.metric(
                            "Datos Transferidos",
                            format_bytes(comparacion['periodo2']['size']),
                            delta=f"{format_bytes(diff_size['absoluta'])} ({diff_size['porcentual']:+.1f}%)"
                        )
                    
                    # Métricas adicionales para sesiones
                    if use_sessions:
                        st.markdown("---")
                        st.subheader("📈 Métricas de Sesiones")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        sessions1 = comparacion['periodo1']['sessions_stats']
                        sessions2 = comparacion['periodo2']['sessions_stats']
                        
                        with col1:
                            if sessions1:
                                avg_pv1 = sessions1.get('avg_pageviews_per_session', 0)
                                avg_pv2 = sessions2.get('avg_pageviews_per_session', 0)
                                diff_pv = ((avg_pv2 - avg_pv1) / avg_pv1 * 100) if avg_pv1 > 0 else 0
                                
                                st.metric(
                                    "Promedio Páginas/Sesión",
                                    f"{avg_pv2:.1f}",
                                    delta=f"{diff_pv:+.1f}%"
                                )
                        
                        with col2:
                            if sessions1:
                                avg_dur1 = sessions1.get('avg_session_duration_minutes', 0)
                                avg_dur2 = sessions2.get('avg_session_duration_minutes', 0)
                                diff_dur = ((avg_dur2 - avg_dur1) / avg_dur1 * 100) if avg_dur1 > 0 else 0
                                
                                st.metric(
                                    "Duración Promedio (min)",
                                    f"{avg_dur2:.1f}",
                                    delta=f"{diff_dur:+.1f}%"
                                )
                    
                    # Gráfico comparativo
                    st.markdown("---")
                    chart_title = "Sesiones Diarias - Comparación" if use_sessions else "Requests Diarios - Comparación"
                    st.subheader(f"📈 {chart_title}")
                    
                    # Preparar datos para gráfico
                    df_p1 = comparacion['dataframes']['periodo1'].copy()
                    df_p2 = comparacion['dataframes']['periodo2'].copy()
                    
                    if not df_p1.empty and not df_p2.empty:
                        # Agrupar por día
                        df_p1['date_only'] = pd.to_datetime(df_p1['date'])
                        df_p2['date_only'] = pd.to_datetime(df_p2['date'])
                        
                        if use_sessions and 'session_id' in df_p1.columns:
                            # Contar sesiones únicas por día
                            requests_p1 = df_p1.groupby('date_only')['session_id'].nunique().reset_index(name='sessions')
                            requests_p2 = df_p2.groupby('date_only')['session_id'].nunique().reset_index(name='sessions')
                            
                            requests_p1['periodo'] = 'Período 1'
                            requests_p2['periodo'] = 'Período 2'
                            
                            # Combinar datos
                            df_combined = pd.concat([requests_p1, requests_p2])
                            
                            fig = px.line(
                                df_combined,
                                x='date_only',
                                y='sessions',
                                color='periodo',
                                title="Comparación de Sesiones Diarias",
                                labels={'date_only': 'Fecha', 'sessions': 'Número de Sesiones'},
                                color_discrete_map={'Período 1': '#1f77b4', 'Período 2': '#ff7f0e'}
                            )
                        else:
                            # Análisis tradicional por requests
                            requests_p1 = df_p1.groupby('date_only').size().reset_index(name='requests')
                            requests_p2 = df_p2.groupby('date_only').size().reset_index(name='requests')
                            
                            requests_p1['periodo'] = 'Período 1'
                            requests_p2['periodo'] = 'Período 2'
                            
                            # Combinar datos
                            df_combined = pd.concat([requests_p1, requests_p2])
                            
                            fig = px.line(
                                df_combined,
                                x='date_only',
                                y='requests',
                                color='periodo',
                                title="Comparación de Requests Diarios",
                                labels={'date_only': 'Fecha', 'requests': 'Número de Requests'},
                                color_discrete_map={'Período 1': '#1f77b4', 'Período 2': '#ff7f0e'}
                            )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Análisis de GA4-like
                    if use_sessions and exclude_bots:
                        st.markdown("---")
                        st.subheader("📊 Análisis Estilo GA4")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**🔵 Período 1**")
                            if sessions1:
                                st.write(f"• **Sesiones:** {sessions1.get('total_sessions', 0):,}")
                                st.write(f"• **Usuarios:** {sessions1.get('unique_users', 0):,}")
                                st.write(f"• **Páginas vistas:** {comparacion['periodo1']['stats'].get('total_requests', 0):,}")
                                st.write(f"• **Páginas/sesión:** {sessions1.get('avg_pageviews_per_session', 0):.1f}")
                                st.write(f"• **Duración promedio:** {sessions1.get('avg_session_duration_minutes', 0):.1f} min")
                        
                        with col2:
                            st.markdown("**🔴 Período 2**")
                            if sessions2:
                                st.write(f"• **Sesiones:** {sessions2.get('total_sessions', 0):,}")
                                st.write(f"• **Usuarios:** {sessions2.get('unique_users', 0):,}")
                                st.write(f"• **Páginas vistas:** {comparacion['periodo2']['stats'].get('total_requests', 0):,}")
                                st.write(f"• **Páginas/sesión:** {sessions2.get('avg_pageviews_per_session', 0):.1f}")
                                st.write(f"• **Duración promedio:** {sessions2.get('avg_session_duration_minutes', 0):.1f} min")
                    
                    # Comparación de códigos de estado
                    st.markdown("---")
                    st.subheader("📊 Comparación de Códigos de Estado")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🔵 Período 1 - Status Codes**")
                        if comparacion['periodo1']['stats'].get('status_codes'):
                            status_p1 = comparacion['periodo1']['stats']['status_codes']
                            status_df_p1 = pd.DataFrame.from_dict(status_p1, orient='index', columns=['Requests']).reset_index()
                            status_df_p1.columns = ['Status Code', 'Requests']
                            st.dataframe(status_df_p1, use_container_width=True)
                            
                            # Gráfico de pie
                            fig_p1 = px.pie(
                                values=list(status_p1.values()),
                                names=list(status_p1.keys()),
                                title=f"Status Codes ({periodo1_inicio} - {periodo1_fin})"
                            )
                            st.plotly_chart(fig_p1, use_container_width=True)
                    
                    with col2:
                        st.markdown("**🔴 Período 2 - Status Codes**")
                        if comparacion['periodo2']['stats'].get('status_codes'):
                            status_p2 = comparacion['periodo2']['stats']['status_codes']
                            status_df_p2 = pd.DataFrame.from_dict(status_p2, orient='index', columns=['Requests']).reset_index()
                            status_df_p2.columns = ['Status Code', 'Requests']
                            st.dataframe(status_df_p2, use_container_width=True)
                            
                            # Gráfico de pie
                            fig_p2 = px.pie(
                                values=list(status_p2.values()),
                                names=list(status_p2.keys()),
                                title=f"Status Codes ({periodo2_inicio} - {periodo2_fin})"
                            )
                            st.plotly_chart(fig_p2, use_container_width=True)
                    
                    # Top IPs comparación
                    st.markdown("---")
                    st.subheader("🌐 Top 10 IPs - Comparación")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🔵 Período 1**")
                        if not df_p1.empty:
                            top_ips_p1 = df_p1['ip'].value_counts().head(10)
                            ip_df_p1 = top_ips_p1.reset_index()
                            ip_df_p1.columns = ['IP', 'Requests']
                            st.dataframe(ip_df_p1, use_container_width=True)
                            
                            # Gráfico de barras horizontal
                            fig_ips_p1 = px.bar(
                                ip_df_p1,
                                x='Requests',
                                y='IP',
                                orientation='h',
                                title="Top IPs - Período 1",
                                color_discrete_sequence=['#1f77b4']
                            )
                            fig_ips_p1.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_ips_p1, use_container_width=True)
                    
                    with col2:
                        st.markdown("**🔴 Período 2**")
                        if not df_p2.empty:
                            top_ips_p2 = df_p2['ip'].value_counts().head(10)
                            ip_df_p2 = top_ips_p2.reset_index()
                            ip_df_p2.columns = ['IP', 'Requests']
                            st.dataframe(ip_df_p2, use_container_width=True)
                            
                            # Gráfico de barras horizontal
                            fig_ips_p2 = px.bar(
                                ip_df_p2,
                                x='Requests',
                                y='IP',
                                orientation='h',
                                title="Top IPs - Período 2",
                                color_discrete_sequence=['#ff7f0e']
                            )
                            fig_ips_p2.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_ips_p2, use_container_width=True)
                    
                    # Comparación de métodos HTTP
                    st.markdown("---")
                    st.subheader("🔧 Comparación de Métodos HTTP")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🔵 Período 1**")
                        if comparacion['periodo1']['stats'].get('methods'):
                            methods_p1 = comparacion['periodo1']['stats']['methods']
                            methods_df_p1 = pd.DataFrame.from_dict(methods_p1, orient='index', columns=['Requests']).reset_index()
                            methods_df_p1.columns = ['Método', 'Requests']
                            st.dataframe(methods_df_p1, use_container_width=True)
                    
                    with col2:
                        st.markdown("**🔴 Período 2**")
                        if comparacion['periodo2']['stats'].get('methods'):
                            methods_p2 = comparacion['periodo2']['stats']['methods']
                            methods_df_p2 = pd.DataFrame.from_dict(methods_p2, orient='index', columns=['Requests']).reset_index()
                            methods_df_p2.columns = ['Método', 'Requests']
                            st.dataframe(methods_df_p2, use_container_width=True)
                    
                    # Análisis de tendencias
                    st.markdown("---")
                    st.subheader("📈 Análisis de Tendencias")
                    
                    tendencias = []
                    
                    # Requests/Sesiones
                    metric_name = "sesiones" if use_sessions else "requests"
                    if diff_requests['porcentual'] > 10:
                        tendencias.append(f"📈 **Incremento significativo en {metric_name}** (+{diff_requests['porcentual']:.1f}%)")
                    elif diff_requests['porcentual'] < -10:
                        tendencias.append(f"📉 **Disminución significativa en {metric_name}** ({diff_requests['porcentual']:.1f}%)")
                    else:
                        tendencias.append(f"➡️ **Tráfico estable** ({diff_requests['porcentual']:.1f}% de cambio)")
                    
                    # Usuarios/IPs únicas
                    user_name = "usuarios únicos" if use_sessions else "IPs únicas"
                    if diff_ips['porcentual'] > 15:
                        tendencias.append(f"👥 **Aumento notable de {user_name}** (+{diff_ips['porcentual']:.1f}%)")
                    elif diff_ips['porcentual'] < -15:
                        tendencias.append(f"👤 **Disminución de {user_name}** ({diff_ips['porcentual']:.1f}%)")
                    
                    # Errores
                    if diff_errors['porcentual'] > 20:
                        tendencias.append(f"⚠️ **Incremento preocupante de errores** (+{diff_errors['porcentual']:.1f}%)")
                    elif diff_errors['porcentual'] < -20:
                        tendencias.append(f"✅ **Mejora en la estabilidad** (errores -{abs(diff_errors['porcentual']):.1f}%)")
                    
                    # Transferencia de datos
                    if diff_size['porcentual'] > 25:
                        tendencias.append(f"📊 **Aumento significativo en transferencia de datos** (+{diff_size['porcentual']:.1f}%)")
                    elif diff_size['porcentual'] < -25:
                        tendencias.append(f"📉 **Reducción en transferencia de datos** ({diff_size['porcentual']:.1f}%)")
                    
                    # Análisis de calidad del tráfico (solo si se excluyen bots)
                    if exclude_bots:
                        if use_sessions and sessions1 and sessions2:
                            avg_pv1 = sessions1.get('avg_pageviews_per_session', 0)
                            avg_pv2 = sessions2.get('avg_pageviews_per_session', 0)
                            if avg_pv2 > avg_pv1 * 1.1:
                                tendencias.append(f"📖 **Mejora en engagement** (páginas por sesión +{((avg_pv2-avg_pv1)/avg_pv1*100):.1f}%)")
                            elif avg_pv2 < avg_pv1 * 0.9:
                                tendencias.append(f"📄 **Disminución en engagement** (páginas por sesión {((avg_pv2-avg_pv1)/avg_pv1*100):.1f}%)")
                    
                    for i, tendencia in enumerate(tendencias):
                        st.markdown(tendencia)
                        if i < len(tendencias) - 1:
                            st.markdown("")
                    
                    # Resumen ejecutivo
                    st.markdown("---")
                    st.subheader("📋 Resumen Ejecutivo")
                    
                    # Determinar el veredicto general
                    if diff_requests['porcentual'] > 5:
                        veredicto_general = "📈 **Crecimiento Positivo**"
                        color = "success"
                    elif diff_requests['porcentual'] < -5:
                        veredicto_general = "📉 **Decrecimiento**"
                        color = "error"
                    else:
                        veredicto_general = "➡️ **Estabilidad**"
                        color = "info"
                    
                    if color == "success":
                        st.success(veredicto_general)
                    elif color == "error":
                        st.error(veredicto_general)
                    else:
                        st.info(veredicto_general)
                    
                    # Métricas clave en formato tabla
                    resumen_data = {
                        'Métrica': [
                            f'{metric_name.title()}',
                            f'{user_name.title()}',
                            'Errores',
                            'Datos Transferidos'
                        ],
                        'Período 1': [
                            f"{comparacion['periodo1']['requests']:,}",
                            f"{comparacion['periodo1']['ips']:,}",
                            f"{comparacion['periodo1']['errors']:,}",
                            format_bytes(comparacion['periodo1']['size'])
                        ],
                        'Período 2': [
                            f"{comparacion['periodo2']['requests']:,}",
                            f"{comparacion['periodo2']['ips']:,}",
                            f"{comparacion['periodo2']['errors']:,}",
                            format_bytes(comparacion['periodo2']['size'])
                        ],
                        'Cambio (%)': [
                            f"{diff_requests['porcentual']:+.1f}%",
                            f"{diff_ips['porcentual']:+.1f}%",
                            f"{diff_errors['porcentual']:+.1f}%",
                            f"{diff_size['porcentual']:+.1f}%"
                        ]
                    }
                    
                    df_resumen = pd.DataFrame(resumen_data)
                    st.table(df_resumen)
                    
                    # Botones de exportación
                    st.markdown("---")
                    st.subheader("💾 Exportar Resultados")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Crear resumen completo para exportar
                        df_export = pd.DataFrame([{
                            'Período 1 - Inicio': str(periodo1_inicio),
                            'Período 1 - Fin': str(periodo1_fin),
                            'Período 1 - Requests/Sesiones': comparacion['periodo1']['requests'],
                            'Período 1 - IPs/Usuarios': comparacion['periodo1']['ips'],
                            'Período 1 - Errores': comparacion['periodo1']['errors'],
                            'Período 1 - Bots Filtrados': comparacion['periodo1']['bots_filtrados'],
                            'Período 2 - Inicio': str(periodo2_inicio),
                            'Período 2 - Fin': str(periodo2_fin),
                            'Período 2 - Requests/Sesiones': comparacion['periodo2']['requests'],
                            'Período 2 - IPs/Usuarios': comparacion['periodo2']['ips'],
                            'Período 2 - Errores': comparacion['periodo2']['errors'],
                            'Período 2 - Bots Filtrados': comparacion['periodo2']['bots_filtrados'],
                            'Cambio Requests/Sesiones (%)': diff_requests['porcentual'],
                            'Cambio IPs/Usuarios (%)': diff_ips['porcentual'],
                            'Cambio Errores (%)': diff_errors['porcentual'],
                            'Cambio Datos (%)': diff_size['porcentual'],
                            'Filtrar Bots': exclude_bots,
                            'Análisis por Sesiones': use_sessions,
                            'Timeout Sesión (min)': session_timeout,
                            'Fecha Análisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }])
                        
                        csv_resumen = df_export.to_csv(index=False)
                        
                        st.download_button(
                            label="📥 Descargar Resumen CSV",
                            data=csv_resumen,
                            file_name=f"comparacion_resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # Exportar datos detallados del período 1
                        if not df_p1.empty:
                            csv_p1 = df_p1.to_csv(index=False)
                            st.download_button(
                                label="📥 Datos Período 1",
                                data=csv_p1,
                                file_name=f"periodo1_{periodo1_inicio}_{periodo1_fin}.csv",
                                mime="text/csv"
                            )
                    
                    with col3:
                        # Exportar datos detallados del período 2
                        if not df_p2.empty:
                            csv_p2 = df_p2.to_csv(index=False)
                            st.download_button(
                                label="📥 Datos Período 2",
                                data=csv_p2,
                                file_name=f"periodo2_{periodo2_inicio}_{periodo2_fin}.csv",
                                mime="text/csv"
                            )
                    
                    # Botón para nueva comparación
                    st.markdown("---")
                    if st.button("🔄 Nueva Comparación", key="nueva_comparacion"):
                        st.rerun()
        
        except Exception as e:
            st.error(f"Error procesando fechas: {e}")
            st.error("Verifica que los datos estén cargados correctamente y las fechas sean válidas")

# Footer con información adicional
st.markdown("---")
st.markdown("### ℹ️ Información del Sistema")
col1, col2, col3 = st.columns(3)

with col1:
    if not st.session_state.df.empty:
        st.metric("Memoria DataFrame", f"{st.session_state.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

with col2:
    if not st.session_state.df.empty:
        st.metric("Filas Procesadas", f"{len(st.session_state.df):,}")

with col3:
    if not st.session_state.df.empty:
        st.metric("Columnas", f"{len(st.session_state.df.columns)}")