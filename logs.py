import pandas as pd
import re
import os

def vista_simple_log(archivo_log, num_lineas=10):
    """
    Muestra las primeras líneas del archivo de log de forma simple
    """
    try:
        print(f"=== ANALIZANDO: {archivo_log} ===\n")
        
        with open(archivo_log, 'r', encoding='utf-8', errors='ignore') as file:
            lineas = []
            contador = 0
            
            for linea in file:
                if contador >= num_lineas:
                    break
                linea_limpia = linea.strip()
                if linea_limpia:  # Solo líneas no vacías
                    lineas.append(linea_limpia)
                    contador += 1
        
        print("Primeras líneas del archivo:")
        print("-" * 50)
        for i, linea in enumerate(lineas):
            print(f"{i+1:2d}: {linea}")
        
        return lineas
        
    except Exception as e:
        print(f"Error al leer archivo: {e}")
        return []

def analizar_separadores(lineas):
    """
    Analiza qué separadores podrían funcionar
    """
    if not lineas:
        return
    
    print(f"\n=== ANÁLISIS DE SEPARADORES ===")
    
    separadores = {
        'espacio': ' ',
        'tab': '\t', 
        'coma': ',',
        'punto_coma': ';',
        'pipe': '|'
    }
    
    primera_linea = lineas[0]
    print(f"\nAnalizando primera línea: {primera_linea}")
    
    for nombre, sep in separadores.items():
        partes = primera_linea.split(sep)
        num_partes = len(partes)
        
        if num_partes > 1:
            print(f"\nSeparador '{nombre}' ({repr(sep)}):")
            print(f"  - Número de columnas: {num_partes}")
            
            # Mostrar primeras 5 partes
            for i in range(min(5, num_partes)):
                parte = partes[i].strip()
                if parte:
                    print(f"  - Columna {i+1}: '{parte}'")

def detectar_patrones(lineas):
    """
    Detecta patrones comunes en las líneas
    """
    if not lineas:
        return
    
    print(f"\n=== PATRONES DETECTADOS ===")
    
    patrones = {
        'fecha_yyyy-mm-dd': r'\d{4}-\d{2}-\d{2}',
        'fecha_dd/mm/yyyy': r'\d{2}/\d{2}/\d{4}',
        'hora': r'\d{2}:\d{2}:\d{2}',
        'ip': r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
        'nivel_log': r'\b(DEBUG|INFO|WARN|ERROR|FATAL|TRACE)\b',
        'status_http': r'\b[1-5]\d{2}\b',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    }
    
    total_lineas = len(lineas)
    
    for patron_nombre, patron_regex in patrones.items():
        coincidencias = 0
        for linea in lineas:
            if re.search(patron_regex, linea, re.IGNORECASE):
                coincidencias += 1
        
        if coincidencias > 0:
            porcentaje = (coincidencias / total_lineas) * 100
            print(f"  - {patron_nombre}: {coincidencias}/{total_lineas} líneas ({porcentaje:.1f}%)")

def crear_dataframe_simple(archivo_log):
    """
    Crea un DataFrame de forma interactiva y simple
    """
    print(f"\n=== CREANDO DATAFRAME ===")
    
    try:
        # Leer todas las líneas
        with open(archivo_log, 'r', encoding='utf-8', errors='ignore') as file:
            todas_lineas = []
            for linea in file:
                linea_limpia = linea.strip()
                if linea_limpia:
                    todas_lineas.append(linea_limpia)
        
        print(f"Total de líneas leídas: {len(todas_lineas)}")
        
        # Pedir separador al usuario
        print("\nOpciones de separador:")
        print("1. Espacio")
        print("2. Tab")
        print("3. Coma")
        print("4. Punto y coma")
        print("5. Pipe (|)")
        
        opcion = input("Elige una opción (1-5): ").strip()
        
        separadores_map = {
            '1': ' ',
            '2': '\t',
            '3': ',', 
            '4': ';',
            '5': '|'
        }
        
        separador = separadores_map.get(opcion, ' ')
        
        # Procesar líneas
        datos = []
        for linea in todas_lineas:
            partes = [parte.strip() for parte in linea.split(separador)]
            partes = [parte for parte in partes if parte]  # Remover vacíos
            if partes:  # Solo agregar si hay datos
                datos.append(partes)
        
        if not datos:
            print("No se pudieron extraer datos.")
            return None
        
        # Encontrar el número máximo de columnas
        max_columnas = max(len(fila) for fila in datos)
        
        # Crear nombres de columnas
        nombres_columnas = []
        for i in range(max_columnas):
            nombre = input(f"Nombre para columna {i+1} (o Enter para 'col_{i+1}'): ").strip()
            if not nombre:
                nombre = f'col_{i+1}'
            nombres_columnas.append(nombre)
        
        # Rellenar filas cortas con valores vacíos
        for fila in datos:
            while len(fila) < max_columnas:
                fila.append('')
        
        # Crear DataFrame
        df = pd.DataFrame(datos, columns=nombres_columnas)
        
        print(f"\nDataFrame creado exitosamente!")
        print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
        print("\nPrimeras 5 filas:")
        print(df.head())
        
        # Guardar opcionalmente
        guardar = input("\n¿Guardar como CSV? (s/n): ").lower().startswith('s')
        if guardar:
            nombre_archivo = archivo_log.replace('.log', '').replace('.txt', '') + '_dataframe.csv'
            df.to_csv(nombre_archivo, index=False)
            print(f"Guardado como: {nombre_archivo}")
        
        return df
        
    except Exception as e:
        print(f"Error al crear DataFrame: {e}")
        return None

def main():
    """
    Función principal
    """
    try:
        # Buscar archivos en el directorio actual
        archivos_posibles = []
        for archivo in os.listdir('.'):
            if archivo.endswith(('.log', '.txt', '.csv')):
                archivos_posibles.append(archivo)
        
        if archivos_posibles:
            print("Archivos encontrados:")
            for i, archivo in enumerate(archivos_posibles, 1):
                print(f"{i}. {archivo}")
            
            if len(archivos_posibles) == 1:
                archivo_elegido = archivos_posibles[0]
                print(f"\nUsando: {archivo_elegido}")
            else:
                try:
                    indice = int(input("\nElige un archivo (número): ")) - 1
                    archivo_elegido = archivos_posibles[indice]
                except (ValueError, IndexError):
                    print("Opción inválida, usando el primer archivo.")
                    archivo_elegido = archivos_posibles[0]
        else:
            archivo_elegido = input("No se encontraron archivos. Ingresa la ruta: ")
        
        # Analizar archivo
        lineas = vista_simple_log(archivo_elegido)
        
        if lineas:
            analizar_separadores(lineas)
            detectar_patrones(lineas)
            
            crear_df = input("\n¿Crear DataFrame? (s/n): ").lower().startswith('s')
            if crear_df:
                df = crear_dataframe_simple(archivo_elegido)
                return df
        
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()