from transform_logs import (
    extract_json_block,
    crear_dataframe,
    get_log_stats
)

import streamlit as st
import pandas as pd

if __name__ == "__main__":
    # Para ejecutar desde línea de comandos
    archivo = "uniite-travel-access.log"
    df, errores = crear_dataframe(archivo, max_lines=1000)
    
    print(f"Datos cargados: {len(df)} filas")
    print(f"Errores: {errores}")
    
    if not df.empty:
        stats = get_log_stats(df)
        print(f"Estadísticas: {stats}")