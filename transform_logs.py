import json
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional
import gc

def extract_json_block(line: str) -> Optional[Dict]:
    """Extrae el bloque JSON de una línea de log"""
    start = line.find('{')
    while start != -1:
        try:
            candidate = line[start:].strip()
            json_data = json.loads(candidate)
            return json_data
        except json.JSONDecodeError:
            start = line.find('{', start + 1)
    return None

def parse_apache_log_line(line: str) -> Optional[Dict]:
    """
    Parsea líneas de log en formato Apache/Nginx Common Log Format
    Formato: IP - - [timestamp] "method path version" status size "referer" "user_agent"
    """
    try:
        # Patrón regex para Apache Common Log Format extendido
        pattern = r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\S+) (\S+) "([^"]*)" "([^"]*)"'
        match = re.match(pattern, line.strip())
        
        if not match:
            # Intentar patrón más simple si el anterior falla
            simple_pattern = r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\S+) (\S+)'
            match = re.match(simple_pattern, line.strip())
            if not match:
                return None
        
        groups = match.groups()
        ip = groups[0]
        timestamp_str = groups[1]
        request = groups[2] if len(groups) > 2 else ""
        status = groups[3] if len(groups) > 3 else "0"
        size = groups[4] if len(groups) > 4 else "0"
        referer = groups[5] if len(groups) > 5 else "-"
        user_agent = groups[6] if len(groups) > 6 else "-"
        
        # Parsear timestamp: [26/May/2025:00:01:08 +0000]
        try:
            dt = datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            try:
                # Intentar sin timezone
                dt = datetime.strptime(timestamp_str.split()[0], "%d/%b/%Y:%H:%M:%S")
            except ValueError:
                dt = datetime.now()  # Fallback
        
        # Parsear request: "GET /path HTTP/1.1"
        method = "-"
        path = "-"
        version = "-"
        
        if request:
            request_parts = request.split()
            if len(request_parts) >= 1:
                method = request_parts[0]
            if len(request_parts) >= 2:
                path = request_parts[1]
            if len(request_parts) >= 3:
                version = request_parts[2]
        
        # Convertir status y size
        try:
            status_code = int(status) if status != "-" and status.isdigit() else 0
        except ValueError:
            status_code = 0
        
        try:
            size_bytes = int(size) if size != "-" and size.isdigit() else 0
        except ValueError:
            size_bytes = 0
        
        return {
            'timestamp': dt,
            'date': dt.date(),
            'time': dt.time(),
            'ip': ip,
            'method': method,
            'path': path,
            'version': version,
            'status_code': status_code,
            'size': size_bytes,
            'referer': referer if referer != "-" else None,
            'user_agent': user_agent if user_agent != "-" else None,
            'raw_line': line.strip()
        }
        
    except Exception as e:
        return None

def parse_log_to_dict(raw_line: str) -> Optional[Dict]:
    """
    Detecta automáticamente el formato del log y lo parsea
    """
    # Primero intentar JSON
    json_result = extract_json_block(raw_line)
    if json_result:
        # Si es JSON, usar el parser JSON original
        try:
            time_str = json_result.get("time", "")
            if not time_str:
                return None
                
            # Intentar diferentes formatos de fecha
            dt = None
            time_formats = [
                "%d/%b/%Y:%H:%M:%S %z",
                "%d/%b/%Y:%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S"
            ]
            
            for fmt in time_formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not dt:
                dt = datetime.now()
            
            return {
                'timestamp': dt,
                'date': dt.date(),
                'time': dt.time(),
                'ip': json_result.get("forwardedfor", json_result.get("remote_addr", "-")),
                'method': json_result.get("method", "-"),
                'path': json_result.get("path", json_result.get("request", "-")),
                'version': json_result.get("version", "-"),
                'status_code': int(json_result.get("code", json_result.get("status", 0))) if str(json_result.get("code", json_result.get("status", ""))).isdigit() else 0,
                'size': int(json_result.get("size", json_result.get("bytes", 0))) if str(json_result.get("size", json_result.get("bytes", ""))).isdigit() else 0,
                'referer': json_result.get("referer", "-"),
                'user_agent': json_result.get("agent", json_result.get("user_agent", "-")),
                'raw_line': raw_line.strip()
            }
        except Exception as e:
            return None
    
    # Si no es JSON, intentar formato Apache
    return parse_apache_log_line(raw_line)

def diagnosticar_archivo(archivo_log: str, num_lineas: int = 10):
    """Diagnostica el formato del archivo de logs"""
    print(f"=== DIAGNÓSTICO DE {archivo_log} ===")
    
    try:
        with open(archivo_log, "r", encoding="utf-8", errors="ignore") as file:
            lineas = []
            for i, line in enumerate(file):
                if i >= num_lineas:
                    break
                lineas.append(line.strip())
        
        print(f"Primeras {len(lineas)} líneas del archivo:")
        print("-" * 50)
        
        json_count = 0
        apache_count = 0
        
        for i, linea in enumerate(lineas, 1):
            print(f"Línea {i}: {linea[:200]}{'...' if len(linea) > 200 else ''}")
            
            # Verificar si tiene JSON
            if '{' in linea:
                json_data = extract_json_block(linea)
                if json_data:
                    print(f"  ✓ JSON válido encontrado")
                    print(f"  Campos JSON: {list(json_data.keys())}")
                    json_count += 1
                else:
                    print(f"  ✗ No se pudo extraer JSON válido")
            
            # Verificar si es formato Apache
            apache_data = parse_apache_log_line(linea)
            if apache_data:
                print(f"  ✓ Formato Apache/Nginx detectado")
                print(f"  IP: {apache_data['ip']}")
                print(f"  Método: {apache_data['method']}")
                print(f"  Path: {apache_data['path']}")
                print(f"  Status: {apache_data['status_code']}")
                apache_count += 1
            else:
                print(f"  ✗ No coincide con formato Apache")
            
            print()
        
        print("=== RESUMEN ===")
        print(f"Líneas con JSON válido: {json_count}")
        print(f"Líneas con formato Apache: {apache_count}")
        
        if apache_count > json_count:
            print("📊 RECOMENDACIÓN: Usar parser de formato Apache/Nginx")
        elif json_count > 0:
            print("📊 RECOMENDACIÓN: Usar parser JSON")
        else:
            print("❌ PROBLEMA: No se detectó ningún formato conocido")
        
        return lineas
        
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return []
    
def is_bot_user_agent(user_agent):
    """
    Detecta si un user agent corresponde a un bot
    """
    if not user_agent or user_agent == "-":
        return False
    
    user_agent_lower = str(user_agent).lower()
    
    # Lista de bots comunes
    bot_patterns = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'facebookexternalhit', 'twitterbot', 'linkedinbot',
        'whatsapp', 'telegram', 'crawler', 'spider', 'scraper',
        'bot', 'crawl', 'fetch', 'monitor', 'check', 'test',
        'pingdom', 'uptime', 'robot', 'wget', 'curl',
        'python-requests', 'scrapy', 'selenium', 'phantomjs',
        'headless', 'apache-httpclient', 'java/', 'go-http-client'
    ]
    
    return any(pattern in user_agent_lower for pattern in bot_patterns)

def filter_bots(df, exclude_bots=True):
    """
    Filtra bots del DataFrame
    """
    if exclude_bots and 'user_agent' in df.columns:
        # Crear máscara para identificar bots
        bot_mask = df['user_agent'].apply(is_bot_user_agent)
        
        # Retornar DataFrame sin bots
        df_filtered = df[~bot_mask].copy()
        
        return df_filtered, bot_mask.sum()  # Retorna DataFrame filtrado y número de bots
    else:
        return df, 0

def create_sessions(df, session_timeout_minutes=30):
    """
    Agrupa requests por sesiones basándose en IP y tiempo
    Una sesión termina si pasan más de session_timeout_minutes sin actividad de la misma IP
    """
    if df.empty:
        return df
    
    # Asegurar que timestamp está ordenado
    df_sorted = df.sort_values(['ip', 'timestamp']).copy()
    
    # Calcular diferencia de tiempo entre requests de la misma IP
    df_sorted['time_diff'] = df_sorted.groupby('ip')['timestamp'].diff()
    
    # Marcar inicio de nueva sesión (primera request de IP o gap > timeout)
    timeout = pd.Timedelta(minutes=session_timeout_minutes)
    df_sorted['new_session'] = (
        df_sorted['time_diff'].isna() | 
        (df_sorted['time_diff'] > timeout)
    )
    
    # Crear ID de sesión
    df_sorted['session_id'] = df_sorted.groupby('ip')['new_session'].cumsum()
    df_sorted['session_id'] = df_sorted['ip'].astype(str) + '_' + df_sorted['session_id'].astype(str)
    
    return df_sorted

def get_session_stats(df_with_sessions):
    """
    Calcula estadísticas basadas en sesiones
    """
    if df_with_sessions.empty or 'session_id' not in df_with_sessions.columns:
        return {}
    
    # Estadísticas por sesión
    session_stats = df_with_sessions.groupby('session_id').agg({
        'timestamp': ['min', 'max', 'count'],
        'ip': 'first',
        'date': 'first'
    }).reset_index()
    
    # Aplanar nombres de columnas
    session_stats.columns = ['session_id', 'session_start', 'session_end', 'pageviews', 'ip', 'date']
    
    # Calcular duración de sesión
    session_stats['session_duration'] = (
        session_stats['session_end'] - session_stats['session_start']
    ).dt.total_seconds() / 60  # en minutos
    
    # Estadísticas generales
    total_sessions = len(session_stats)
    unique_users = session_stats['ip'].nunique()
    avg_pageviews = session_stats['pageviews'].mean()
    avg_duration = session_stats['session_duration'].mean()
    
    # Sesiones por día
    sessions_by_date = session_stats.groupby('date').size()
    
    return {
        'total_sessions': total_sessions,
        'unique_users': unique_users,
        'avg_pageviews_per_session': avg_pageviews,
        'avg_session_duration_minutes': avg_duration,
        'sessions_by_date': sessions_by_date.to_dict(),
        'session_details': session_stats
    }


def crear_dataframe(archivo_log: str, max_lines: Optional[int] = None, chunk_size: int = 10000, progress_callback=None) -> tuple:
    """
    Crea un DataFrame procesando el archivo por chunks para archivos grandes
    """
    print(f"Procesando archivo: {archivo_log}")
    print(f"Máximo de líneas: {max_lines}")
    
    # Primero hacer un diagnóstico
    print("Realizando diagnóstico del archivo...")
    diagnosticar_archivo(archivo_log, 5)
    
    datos = []
    errores = 0
    lineas_procesadas = 0
    lineas_exitosas = 0
    
    try:
        with open(archivo_log, "r", encoding="utf-8", errors="ignore") as file:
            chunk_datos = []
            
            for line_num, line in enumerate(file):
                if max_lines and line_num >= max_lines:
                    break
                
                # Mostrar progreso cada 10000 líneas
                if line_num % 10000 == 0 and line_num > 0:
                    print(f"Procesando línea {line_num}... Exitosas: {lineas_exitosas}")
                
                parsed = parse_log_to_dict(line)
                if parsed:
                    chunk_datos.append(parsed)
                    lineas_exitosas += 1
                else:
                    errores += 1
                    # Mostrar los primeros errores para debug
                    if errores <= 5:
                        print(f"Error en línea {line_num}: {line[:100]}...")
                
                lineas_procesadas += 1
                
                # Procesar chunk cuando alcance el tamaño deseado
                if len(chunk_datos) >= chunk_size:
                    datos.extend(chunk_datos)
                    chunk_datos = []
                    print(f"Chunk procesado: {len(datos)} registros exitosos hasta ahora")
                    
                    # Callback para progreso
                    if progress_callback:
                        progress = min(line_num / max_lines if max_lines else 0.5, 1.0)
                        progress_callback(progress, lineas_procesadas)
                    
                    # Liberar memoria cada cierto número de chunks
                    if len(datos) % 50000 == 0:
                        gc.collect()
            
            # Procesar chunk restante
            if chunk_datos:
                datos.extend(chunk_datos)
        
        print(f"Resumen del procesamiento:")
        print(f"  - Líneas procesadas: {lineas_procesadas}")
        print(f"  - Líneas exitosas: {lineas_exitosas}")
        print(f"  - Errores: {errores}")
        print(f"  - Tasa de éxito: {(lineas_exitosas/lineas_procesadas)*100:.2f}%" if lineas_procesadas > 0 else "0%")
        
        # Crear DataFrame si hay datos
        if datos:
            print("Creando DataFrame...")
            df = pd.DataFrame(datos)
            
            # Optimizar tipos de datos para reducir memoria
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['status_code'] = pd.to_numeric(df['status_code'], errors='coerce', downcast='integer')
            df['size'] = pd.to_numeric(df['size'], errors='coerce', downcast='integer')
            
            # Convertir strings a categorías para ahorrar memoria
            categorical_columns = ['method', 'version', 'ip']
            for col in categorical_columns:
                if col in df.columns:
                    df[col] = df[col].astype('category')
            
            # Liberar memoria
            del datos
            gc.collect()
            
            print(f"DataFrame creado: {len(df)} filas, {len(df.columns)} columnas")
            return df, errores
        else:
            print("No se crearon datos válidos")
            return pd.DataFrame(), errores
        
    except Exception as e:
        print(f"Error al procesar archivo: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), errores

def crear_dataframe_sample(archivo_log: str, sample_size: int = 50000) -> tuple:
    """
    Crea un DataFrame con una muestra aleatoria del archivo para archivos muy grandes
    """
    import random
    
    print(f"Creando muestra aleatoria de {sample_size} líneas...")
    
    try:
        # Primero, contar líneas totales (estimación rápida para archivos grandes)
        print("Estimando número total de líneas...")
        with open(archivo_log, "r", encoding="utf-8", errors="ignore") as file:
            # Para archivos grandes, hacer una estimación
            file.seek(0, 2)  # Ir al final
            file_size = file.tell()
            file.seek(0)  # Volver al inicio
            
            # Leer una muestra pequeña para estimar líneas por byte
            sample = file.read(100000)  # 100KB
            lines_in_sample = sample.count('\n')
            
            if lines_in_sample > 0:
                total_lines = int((file_size / 100000) * lines_in_sample)
            else:
                total_lines = 100000  # Estimación fallback
        
        print(f"Líneas estimadas: {total_lines}")
        
        # Calcular qué líneas muestrear
        if total_lines <= sample_size:
            print("Archivo pequeño, procesando todas las líneas...")
            return crear_dataframe(archivo_log, max_lines=total_lines)
        
        sample_lines = sorted(random.sample(range(total_lines), min(sample_size, total_lines)))
        sample_set = set(sample_lines)
        
        print(f"Muestreando {len(sample_set)} líneas...")
        
        datos = []
        errores = 0
        
        with open(archivo_log, "r", encoding="utf-8", errors="ignore") as file:
            for line_num, line in enumerate(file):
                if line_num in sample_set:
                    parsed = parse_log_to_dict(line)
                    if parsed:
                        datos.append(parsed)
                    else:
                        errores += 1
                        if errores <= 3:  # Mostrar solo los primeros errores
                            print(f"Error en línea {line_num}: {line[:100]}...")
                
                # Mostrar progreso
                if line_num % 100000 == 0 and len(datos) > 0:
                    print(f"Revisadas {line_num} líneas, encontradas {len(datos)} válidas...")
        
        print(f"Muestra completada: {len(datos)} registros válidos, {errores} errores")
        
        if datos:
            df = pd.DataFrame(datos)
            
            # Optimizar tipos de datos
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['status_code'] = pd.to_numeric(df['status_code'], errors='coerce', downcast='integer')
            df['size'] = pd.to_numeric(df['size'], errors='coerce', downcast='integer')
            
            # Convertir a categorías
            categorical_columns = ['method', 'version', 'ip']
            for col in categorical_columns:
                if col in df.columns:
                    df[col] = df[col].astype('category')
            
            return df, errores
        else:
            return pd.DataFrame(), errores
            
    except Exception as e:
        print(f"Error al crear muestra: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), errores

def get_log_stats(df: pd.DataFrame) -> Dict:
    """Obtiene estadísticas básicas del DataFrame"""
    if df.empty:
        return {}
    
    return {
        'total_requests': len(df),
        'unique_ips': df['ip'].nunique(),
        'date_range': (df['date'].min(), df['date'].max()) if not df.empty else (None, None),
        'status_codes': df['status_code'].value_counts().to_dict(),
        'methods': df['method'].value_counts().to_dict(),
        'total_size': df['size'].sum(),
        'avg_size': df['size'].mean(),
        'errors': len(df[df['status_code'] >= 400])
    }