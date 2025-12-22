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
        # LIMPIEZA DE COLUMNAS: Quitamos espacios y pasamos a minúsculas
        df_acopios.columns = df_acopios.columns.str.strip().str.lower()
    except Exception as e:
        st.error(f"⚠️ Error al leer el Excel: {e}")
        df_acopios = pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])
    return precios, df_acopios

precios_hoy, df_acopios = cargar_datos()

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.header("⚙️ Parámetros")
    grano_sel = st.selectbox("Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas", min_value=1.0, value=30.0)
    precio_base = precios_hoy[grano_sel]
    st.metric(f"Pizarra {grano_sel}", f"USD {precio_base}")

# 4. MAPA
st.title("🌾 Comparador de Destinos Logísticos")
st.markdown("Haz clic en tu lote para ver acopios (radio 50km) y puertos.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)

# Puertos fijos
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]

for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], 
                  icon=folium.Icon(color="red", icon="anchor", prefix="fa")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. CÁLCULOS
if mapa_data.get("last_clicked"):
    u_lat = mapa_data["last_clicked"]["lat"]
    u_lon = mapa_data["last_clicked"]["lng"]
    
    resultados = []
    
    # Evaluar Puertos
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete = (d * 1350) / 1050
        neto_usd = (precio_base - costo_flete) * toneladas
        resultados.append({"Destino": p['nombre'], "Tipo": "Puerto", "KM": d, "Neto Total USD": neto_usd})
        
    # Evaluar Acopios del Excel (con manejo de errores por si las columnas fallan)
    if not df_acopios.empty and 'lat' in df_acopios.columns:
        for _, row in df_acopios.iterrows():
            try:
                # Usamos los nombres ya normalizados
                coords_acopio = (row['lat'], row['lon'])
                d = geodesic((u_lat, u_lon), coords_acopio).kilometers
                
                if d <= 50:
                    costo_flete = (d * 1350) / 1050
                    # Descuento de 7 USD por ser acopio local vs puerto
                    neto_usd = (precio_base - 7 - costo_flete) * toneladas
                    resultados.append({
                        "Destino": row['nombre'], 
                        "Tipo": row.get('tipo', 'Acopio'), 
                        "KM": d, 
                        "Neto Total USD": neto_usd
                    })
            except:
                continue
            
    if resultados:
        df_res = pd.DataFrame(resultados).sort_values(by="Neto Total USD", ascending=False)
        st.subheader("📊 Tabla de Rentabilidad")
        st.dataframe(df_res.style.format({"KM": "{:.1f}", "Neto Total USD": "{:.2f}"}), use_container_width=True)
        
        mejor = df_res.iloc[0]
        st.success(f"✅ La mejor opción es **{mejor['Destino']}** a {mejor['KM']:.1f} km.")
    else:
        st.warning("No se encontraron resultados. Intenta marcar otro punto en el mapa.")


