import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística AR 2025", layout="wide")

# 2. FUNCIÓN PARA OBTENER PRECIOS REALES (SIMULADA PARA 2025)
def obtener_precios_agro():
    # En una fase avanzada, aquí se conectaría con la API de la BCR o MATba-ROFEX
    return {
        "Soja": 298.50,
        "Maíz": 175.20,
        "Trigo": 210.00,
        "Girasol": 315.00
    }

precios_hoy = obtener_precios_agro()

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.title("🌾 Configuración")
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas a comercializar", min_value=1, value=30)
    
    st.divider()
    precio_unidad = precios_hoy[grano_sel]
    st.metric(label=f"Precio Pizarra {grano_sel} (USD/tn)", value=f"US$ {precio_unidad}")
    st.info("Datos actualizados al 21 de Diciembre 2025")

# 4. CUERPO PRINCIPAL
st.title("🚜 Optimizador Logístico Agrícola Argentina")
st.markdown("Haz clic en el mapa sobre la **ubicación de tu lote** para analizar destinos.")

# Definición de Puertos/Destinos
destinos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393, "operador": "Viterra / Cargill"},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664, "operador": "ADM / Dreyfus"},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131, "operador": "ACA / COFCO"}
]

# Crear Mapa
m = folium.Map(location=[-34.6, -61.0], zoom_start=6)

# Marcadores de Puertos
for d in destinos:
    folium.Marker(
        [d['lat'], d['lon']], 
        popup=d['nombre'],
        icon=folium.Icon(color="blue", icon="ship", prefix='fa')
    ).add_to(m)

# Captura de clic
mapa_data = st_folium(m, width="100%", height=450)


# 5. LÓGICA DE CÁLCULO Y LOGÍSTICA
if mapa_data.get("last_clicked"):
    user_lat = mapa_data["last_clicked"]["lat"]
    user_lon = mapa_data["last_clicked"]["lng"]
    
    st.subheader("📊 Análisis de Rentabilidad")
    
    resultados = []
    for d in destinos:
        dist = geodesic((user_lat, user_lon), (d['lat'], d['lon'])).kilometers
        # Cálculo de flete (Estimado 2025: $1.200 ARS por km / $1.050 TC)
        costo_flete_total = (dist * 1200 * (toneladas/30)) / 1050
        ingreso_bruto = precio_unidad * toneladas
        margen_neto = ingreso_bruto - costo_flete_total
        
        resultados.append({
            "Destino": d['nombre'],
            "Distancia (km)": round(dist, 1),
            "Ingreso Bruto (USD)": round(ingreso_bruto, 2),
            "Costo Flete (USD)": round(costo_flete_total, 2),
            "Margen Neto (USD)": round(margen_neto, 2)
        })
    
    df_res = pd.DataFrame(resultados).sort_values(by="Margen Neto (USD)", ascending=False)
    
    # Mostrar resultados
    st.table(df_res)
    
    mejor_destino = df_res.iloc[0]['Destino']
    st.success(f"✅ La opción más rentable es **{mejor_destino}**.")
    
    

# --- CUADRO COMPARATIVO DE COMERCIALIZACIÓN ---
if mapa_data.get("last_clicked"):
    user_lat = mapa_data["last_clicked"]["lat"] # 6. MÓDULO DE LOGÍSTICA OPERATIVA 2025
    st.divider()
    st.header("🚚 Planificación Logística Avanzada")
    
    col_log1, col_log2 = st.columns(2)
    
    with col_log1:
        st.subheader("📦 Gestión de Flota")
        capacidad_camion = 30 # toneladas promedio en Argentina
        cant_camiones = (toneladas // capacidad_camion) + (1 if toneladas % capacidad_camion > 0 else 0)
        
        st.write(f"Para mover **{toneladas} tn**, necesitas:")
        st.metric("Camiones Necesarios", f"{cant_camiones} viajes")
        
        tarifa_referencia_catac = 1450 # Pesos por km aprox Dic 2025
        costo_total_pesos = cant_camiones * mejor_opcion['Distancia (km)'] * tarifa_referencia_catac
        st.write(f"Presupuesto estimado flete: **ARS {costo_total_pesos:,.0f}**")

    with col_log2:
        st.subheader("⚠️ Estado de Rutas y Puertos")
        # Simulación de estados de rutas argentinas 2025
        if "Rosario" in mejor_opcion['Puerto/Destino']:
            st.warning("Ruta Nacional 34: Congestión elevada en zona A012.")
            st.error("Demora en descarga: 6.5 horas (Puerto Rosario Norte)")
        elif "Bahía Blanca" in mejor_opcion['Puerto/Destino']:
            st.success("Ruta Nacional 3: Tránsito fluido.")
            st.info("Demora en descarga: 2 horas (Ingeniero White)")
        else:
            st.info("Ruta Nacional 226: Obras menores en cercanías a Balcarce.")

    # 7. BOTÓN DE OPTIMIZACIÓN CON IA
    st.divider()
    if st.button("🤖 Generar Hoja de Ruta Inteligente"):
        with st.spinner('Analizando variables climáticas y de tráfico...'):
            # Lógica de recomendación logística
            st.balloons()
            st.subheader("📋 Hoja de Ruta Sugerida por IA")
            
            # Cálculo de tiempo de viaje (promedio 60km/h camión)
            dist_num = float(mejor_opcion['Distancia (km)'].split()[0])
            tiempo_viaje = dist_num / 60
            
            st.write(f"1. **Salida óptima:** Mañana 04:30 AM para evitar hora pico en accesos.")
            st.write(f"2. **Ruta recomendada:** Evitar caminos de tierra si hay pronóstico de lluvia (Radar indica 20% probabilidad).")
            st.write(f"3. **Cupo:** Se recomienda solicitar cupo para la 'Ventana 2' (12:00 a 18:00 hs).")
            
            # Exportar datos para el transportista
            datos_chofer = f"Carga: {toneladas}tn {grano_sel} | Destino: {mejor_opcion['Puerto/Destino']} | KM: {dist_num}"
            st.download_button("Descargar Instrucciones para Transportista", datos_chofer, file_name="hoja_ruta.txt")
    user_lon = mapa_data["last_clicked"]["lng"]

    st.subheader("📊 Comparativa de Destinos Sugeridos")
    st.markdown("Cálculos basados en precios de pizarra y tarifas de flete estimadas para diciembre 2025.")

    analisis = []
    for d in destinos:
        # 1. Calcular distancia real desde el punto del mapa
        distancia_km = geodesic((user_lat, user_lon), (d['lat'], d['lon'])).kilometers
        
        # 2. Lógica de Costos (Valores promedio Argentina 2025)
        # Estimamos un flete de $1.350 ARS por km/tonelada
        costo_flete_usd_tn = (distancia_km * 1350) / 1050  # Convertido a USD (TC 1050)
        
        # 3. Cálculo de Ingresos
        precio_final_tn = precio_unidad - costo_flete_usd_tn
        total_operacion = precio_final_tn * toneladas

        analisis.append({
            "Puerto/Destino": d['nombre'],
            "Empresa Principal": d['operador'],
            "Distancia (km)": f"{distancia_km:.1f} km",
            "Costo Flete (USD/tn)": f"US$ {costo_flete_usd_tn:.2f}",
            "Precio Neto (USD/tn)": f"US$ {precio_final_tn:.2f}",
            "Resultado Total (USD)": total_operacion
        })

    # Crear DataFrame para la tabla
    df_comparativo = pd.DataFrame(analisis)

    # Mostrar la tabla con formato destacado
    st.dataframe(
        df_comparativo.sort_values(by="Resultado Total (USD)", ascending=False),
        column_config={
            "Resultado Total (USD)": st.column_config.NumberColumn(
                "Margen Total (USD)",
                help="Dinero neto estimado tras pagar flete",
                format="US$ %.2f"
            ),
        },
        hide_index=True,
        use_container_width=True
    )

    # Resumen de IA para toma de decisión rápida
    mejor_opcion = df_comparativo.sort_values(by="Resultado Total (USD)", ascending=False).iloc[0]
    st.success(f"💡 **Recomendación:** Te conviene comercializar en **{mejor_opcion['Puerto/Destino']}** con **{mejor_opcion['Empresa Principal']}**. Ganarías un neto de **{mejor_opcion['Resultado Total (USD)']:,.2f} USD**.")



