

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística AR 2025", layout="wide", page_icon="🌾")

# 2. FUNCIÓN PARA OBTENER PRECIOS (SIMULADA DIC 2025)
def obtener_precios_agro():
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
    toneladas = st.number_input("Toneladas a comercializar", min_value=1.0, value=30.0)
    
    st.divider()
    precio_unidad = precios_hoy[grano_sel]
    st.metric(label=f"Precio Pizarra {grano_sel} (USD/tn)", value=f"US$ {precio_unidad}")
    st.info("Datos actualizados al 22 de Diciembre 2025")

# 4. CUERPO PRINCIPAL
st.title("🚜 Optimizador Logístico Agrícola Argentina")
st.markdown("Haz clic en el mapa sobre la **ubicación de tu lote** para marcarlo y analizar la logística.")

# Definición de Puertos
destinos_data = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393, "operador": "Viterra / Cargill"},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664, "operador": "ADM / Dreyfus"},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131, "operador": "ACA / COFCO"}
]

# Creación del Mapa
m = folium.Map(location=[-34.6, -61.0], zoom_start=6)

for d in destinos_data:
    folium.Marker(
        [d['lat'], d['lon']], 
        popup=d['nombre'],
        icon=folium.Icon(color="blue", icon="ship", prefix='fa')
    ).add_to(m)

# Mostrar mapa y capturar clic
mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO AL HACER CLIC
if mapa_data.get("last_clicked"):
    user_lat = mapa_data["last_clicked"]["lat"]
    user_lon = mapa_data["last_clicked"]["lng"]
    
    st.success(f"📍 Lote marcado en: {user_lat:.4f}, {user_lon:.4f}")
    
    analisis = []
    for d in destinos_data:
        distancia_km = geodesic((user_lat, user_lon), (d['lat'], d['lon'])).kilometers
        # Flete 2025: $1.350 ARS/km | TC: 1.050
        costo_flete_usd_tn = (distancia_km * 1350) / 1050
        precio_neto_tn = precio_unidad - costo_flete_usd_tn
        total_usd = precio_neto_tn * toneladas
        
        analisis.append({
            "Puerto/Destino": d['nombre'],
            "Empresa Principal": d['operador'],
            "Distancia_KM": distancia_km,
            "Flete_USD_TN": costo_flete_usd_tn,
            "Precio_Neto_TN": precio_neto_tn,
            "Resultado_Total_USD": total_usd
        })
    
    # Crear DataFrame y ordenar
    df_comparativo = pd.DataFrame(analisis).sort_values(by="Resultado_Total_USD", ascending=False)
    
    # Extraer la mejor opción de forma segura para evitar el TypeError
    mejor_opcion = df_comparativo.iloc[0]

    st.subheader("📊 Comparativa de Comercialización")
    st.dataframe(
        df_comparativo,
        column_config={
            "Distancia_KM": st.column_config.NumberColumn("Distancia (km)", format="%.1f"),
            "Flete_USD_TN": st.column_config.NumberColumn("Flete (USD/tn)", format="US$ %.2f"),
            "Precio_Neto_TN": st.column_config.NumberColumn("Neto (USD/tn)", format="US$ %.2f"),
            "Resultado_Total_USD": st.column_config.NumberColumn("Total Neto (USD)", format="US$ %.2f"),
        },
        hide_index=True,
        use_container_width=True
    )

    # 6. MÓDULO DE LOGÍSTICA OPERATIVA
    st.divider()
    st.header("🚚 Planificación Logística")
    
    col_log1, col_log2 = st.columns(2)
    
    with col_log1:
        st.subheader("📦 Gestión de Flota")
        capacidad_camion = 30
        cant_camiones = int((toneladas // capacidad_camion) + (1 if toneladas % capacidad_camion > 0 else 0))
        
        st.metric("Viajes de Camión", f"{cant_camiones}")
        
        # Cálculo corregido con conversión explícita a float
        dist_final = float(mejor_opcion["Distancia_KM"])
        costo_flete_ars = cant_camiones * dist_final * 1350
        st.write(f"Costo operativo flete: **ARS {costo_flete_ars:,.0f}**")

    with col_log2:
        st.subheader("⚠️ Estado de Rutas y Puertos")
        destino_nombre = mejor_opcion["Puerto/Destino"]
        if "Rosario" in destino_nombre:
            st.warning("RN 34: Congestión elevada en accesos.")
            st.error("Demora en descarga: 6.5 horas")
        elif "Bahía Blanca" in destino_nombre:
            st.success("RN 3: Tránsito fluido hacia el sur.")
            st.info("Demora en descarga: 2 horas")
        else:
            st.info("Rutas sin reportes de demoras importantes.")

    # 7. ASISTENTE IA
    st.divider()
    if st.button("🤖 Generar Hoja de Ruta Inteligente"):
        with st.spinner('Analizando variables...'):
            st.balloons()
            st.subheader("📋 Sugerencias de la IA")
            st.write(f"- **Destino sugerido:** {mejor_opcion['Puerto/Destino']}")
            st.write(f"- **Operativo:** Se necesitan {cant_camiones} camiones de 30tn.")
            st.write(f"- **Clima:** Radar de zona núcleo indica condiciones aptas para carga.")
            
            resumen = f"Carga: {toneladas}tn {grano_sel}\nDestino: {mejor_opcion['Puerto/Destino']}\nDistancia: {float(mejor_opcion['Distancia_KM']):.1f} km"
            st.download_button("Descargar Instrucciones Chofer", resumen, file_name="hoja_ruta_agro.txt")
else:
    st.info("👆 Haz clic en el mapa sobre la ubicación de tu lote para calcular la mejor opción logística.")




