import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# 1. CONFIGURACIÓN
st.set_page_config(page_title="AgroLogística Pro 2025", layout="wide")

# 2. CARGA DE DATOS
@st.cache_data
def cargar_datos():
    precios = {"Soja": 298.50, "Maíz": 175.20, "Trigo": 210.00, "Girasol": 315.00}
    try:
        df_acopios = pd.read_excel("acopios_argentina.xlsx")
        df_acopios.columns = df_acopios.columns.str.strip().str.lower()
    except:
        df_acopios = pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])
    return precios, df_acopios

precios_hoy, df_acopios = cargar_datos()

# 3. INTERFAZ LATERAL (Datos Generales)
with st.sidebar:
    st.header("⚙️ Parámetros Generales")
    grano_sel = st.selectbox("Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas", min_value=1.0, value=30.0)
    precio_base = precios_hoy[grano_sel]
    st.metric(f"Pizarra {grano_sel}", f"USD {precio_base}")

# 4. MAPA
st.title("🌾 Comparador y Calculador de Gastos por Destino")
st.markdown("1. Haz clic en tu lote. 2. Selecciona un destino para personalizar gastos.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], icon=folium.Icon(color="red")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. CÁLCULOS INICIALES
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # Procesar Puertos y Acopios
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete = (d * 1350) / 1050
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete USD/tn": costo_flete, "Base": precio_base})
        
    for _, row in df_acopios.iterrows():
        d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
        if d <= 50:
            costo_flete = (d * 1350) / 1050
            resultados.append({"Destino": row['nombre'], "KM": d, "Flete USD/tn": costo_flete, "Base": precio_base - 7})

    if resultados:
        df_res = pd.DataFrame(resultados)
        
        # --- NUEVA SECCIÓN: CARGA MANUAL POR DESTINO ---
        st.divider()
        st.subheader("🎯 Personalización de Gastos por Destino")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            destino_elegido = st.selectbox("Seleccione destino para ajustar:", df_res["Destino"].tolist())
            datos_dest = df_res[df_res["Destino"] == destino_elegido].iloc[0]
            
            st.info(f"Distancia: {datos_dest['KM']:.1f} km")
            st.info(f"Flete base: US$ {datos_dest['Flete USD/tn']:.2f}/tn")

        with col2:
            expander = st.expander("🛠️ Cargar Gastos Manuales para este destino", expanded=True)
            with expander:
                c1, c2, c3 = st.columns(3)
                g_par = c1.number_input("Paritarias", value=0.0)
                g_com = c2.number_input("Comisión", value=0.5)
                g_lab = c3.number_input("Laboratorio", value=0.1)
                g_merv = c1.number_input("Merma Volátil", value=0.2)
                g_fcorto = c2.number_input("Flete Corto", value=0.0)
                g_otros = c3.number_input("Otros", value=0.0)
                
                total_gastos_manuales = sum([g_par, g_com, g_lab, g_merv, g_fcorto, g_otros])
                
        # CÁLCULO FINAL ESPECÍFICO
        neto_final_tn = datos_dest['Base'] - datos_dest['Flete USD/tn'] - total_gastos_manuales
        total_dolares = neto_final_tn * toneladas
        
        st.metric(f"💰 Resultado Neto Final en {destino_elegido}", f"US$ {total_dolares:,.2f}", 
                  delta=f"US$ {neto_final_tn:.2f} por tonelada")
        
        # Tabla comparativa general (con flete base)
        st.write("---")
        st.write("📋 Comparativa rápida (solo flete base):")
        df_res["Neto Est."] = (df_res["Base"] - df_res["Flete USD/tn"]) * toneladas
        st.dataframe(df_res[["Destino", "KM", "Neto Est."]].sort_values("Neto Est.", ascending=False), use_container_width=True)


