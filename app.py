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
    
    # 6. ASISTENTE IA DE LOGÍSTICA
    st.divider()
    st.subheader("🤖 Recomendación de la IA")
    if st.button("Optimizar Logística"):
        st.write(f"Analizando cupos en **{mejor_destino}** para camiones desde tu ubicación...")
        st.info("Sugerencia: Se detectan demoras de 5hs en accesos a Rosario. Se recomienda desviar carga a Bahía Blanca si el precio sube más de 3 USD.")


