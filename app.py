import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística Pro 2025", layout="wide", page_icon="🌾")

# 2. DATOS DE MERCADO 2025
def obtener_precios_agro():
    return {"Soja": 298.50, "Maíz": 175.20, "Trigo": 210.00, "Girasol": 315.00}

precios_hoy = obtener_precios_agro()

# 3. BASE DE DATOS DE ACOPIOS Y COOPERATIVAS (Ejemplos Reales Zona Núcleo)
# En una fase final, esto se conectaría a un Excel o base de datos del RUCA.
acopios_locales = [
    {"nombre": "AFA Pergamino", "lat": -33.8917, "lon": -60.5731, "tipo": "Cooperativa"},
    {"nombre": "Cargill Venado Tuerto", "lat": -33.7456, "lon": -61.9688, "tipo": "Acopio Privado"},
    {"nombre": "Gear S.A. Rojas", "lat": -34.1950, "lon": -60.7322, "tipo": "Acopio Privado"},
    {"nombre": "Coop. Agropecuaria Unión (Justiniano Posse)", "lat": -32.8833, "lon": -62.6667, "tipo": "Cooperativa"},
    {"nombre": "LDC Junín", "lat": -34.5833, "lon": -60.9500, "tipo": "Acopio Privado"},
    {"nombre": "ACA San Nicolás", "lat": -33.3333, "lon": -60.2167, "tipo": "Cooperativa"},
]

destinos_puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393, "tipo": "Puerto Exportador"},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664, "tipo": "Puerto Exportador"},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131, "tipo": "Puerto Exportador"}
]

# 4. INTERFAZ LATERAL
with st.sidebar:
    st.title("🌾 Configuración")
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas", min_value=1.0, value=30.0)
    st.divider()
    precio_unidad = precios_hoy[grano_sel]
    st.metric(label=f"Pizarra {grano_sel} (USD)", value=f"US$ {precio_unidad}")

# 5. MAPA INTERACTIVO
st.title("🚜 Comparador de Comercialización Cercana")
st.markdown("Haz clic en tu campo para ver **Puertos** y **Acopios** en un radio de 50km.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)

# Dibujar Puertos (Siempre visibles)
for p in destinos_puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], 
                  icon=folium.Icon(color="blue", icon="ship", prefix='fa')).add_to(m)

# Captura de clic
mapa_data = st_folium(m, width="100%", height=400)

# 6. LÓGICA DE FILTRADO Y COMPARATIVA
if mapa_data.get("last_clicked"):
    u_lat = mapa_data["last_clicked"]["lat"]
    u_lon = mapa_data["last_clicked"]["lng"]
    
    st.success(f"📍 Lote detectado. Analizando opciones comerciales...")
    
    analisis = []
    
    # Unificamos puertos y acopios para el análisis
    todas_las_opciones = destinos_puertos + acopios_locales
    
    for d in todas_las_opciones:
        dist = geodesic((u_lat, u_lon), (d['lat'], d['lon'])).kilometers
        
        # FILTRO: Solo puertos O acopios a menos de 50km
        if d['tipo'] == "Puerto Exportador" or dist <= 50:
            # Precio diferencial: Acopios suelen pagar 3-5 USD menos que el puerto por logística
            precio_base = precio_unidad if d['tipo'] == "Puerto Exportador" else precio_unidad - 5
            
            flete_usd_tn = (dist * 1350) / 1050
            neto_tn = precio_base - flete_usd_tn
            
            analisis.append({
                "Destino": d['nombre'],
                "Tipo": d['tipo'],
                "Distancia (km)": dist,
                "Precio Neto (USD/tn)": neto_tn,
                "Resultado Total (USD)": neto_tn * toneladas
            })
    
    if analisis:
        df = pd.DataFrame(analisis).sort_values(by="Resultado Total (USD)", ascending=False)
        
        st.subheader("📊 Tabla Comparativa Final")
        st.dataframe(df, column_config={
            "Distancia (km)": st.column_config.NumberColumn(format="%.1f"),
            "Precio Neto (USD/tn)": st.column_config.NumberColumn(format="US$ %.2f"),
            "Resultado Total (USD)": st.column_config.NumberColumn(format="US$ %.2f")
        }, hide_index=True, use_container_width=True)
        
        mejor = df.iloc[0]
        st.success(f"✅ La opción óptima es **{mejor['Destino']}**. Margen total: **US$ {mejor['Resultado Total (USD)']:,.2f}**")
    else:
        st.warning("No se encontraron acopios a menos de 50km. Prueba marcar otro punto.")


