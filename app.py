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

import streamlit as st
import pandas as pd
from geopy.distance import geodesic

# --- NUEVA FUNCIÓN PARA CARGAR DATOS DESDE EXCEL ---
@st.cache_data # Esto hace que la app sea rápida y no cargue el Excel cada vez
def cargar_base_acopios():
    try:
        df = pd.read_excel("acopios_argentina.xlsx")
        return df
    except:
        # Si el archivo no carga, devolvemos una lista vacía para no romper la app
        return pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])

df_acopios_completo = cargar_base_acopios()

# --- DENTRO DE LA LÓGICA DEL CLIC EN EL MAPA ---
if mapa_data.get("last_clicked"):
    u_lat = mapa_data["last_clicked"]["lat"]
    u_lon = mapa_data["last_clicked"]["lng"]
    
    st.info("🔍 Buscando acopios en un radio de 50km...")
    
    analisis = []
    
    # 1. Procesar Acopios del Excel (Filtrado por 50km)
    for index, row in df_acopios_completo.iterrows():
        acopio_coords = (row['lat'], row['lon'])
        dist = geodesic((u_lat, u_lon), acopio_coords).kilometers
        
        if dist <= 50:
            # Cálculo de rentabilidad para acopio local
            precio_acopio = precio_unidad - 7 # Diferencial estimado por acopio
            flete = (dist * 1350) / 1050
            neto = precio_acopio - flete
            
            analisis.append({
                "Destino": row['nombre'],
                "Tipo": "Acopio Local",
                "Distancia (km)": dist,
                "Resultado Total (USD)": neto * toneladas
            })

    # 2. Procesar Puertos (Siempre se incluyen)
    for p in destinos_puertos:
        dist_p = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        flete_p = (dist_p * 1350) / 1050
        neto_p = precio_unidad - flete_p
        
        analisis.append({
            "Destino": p['nombre'],
            "Tipo": "Puerto Exportador",
            "Distancia (km)": dist_p,
            "Resultado Total (USD)": neto_p * toneladas
        })

    # Mostrar la tabla final unificada
    if analisis:
        df_final = pd.DataFrame(analisis).sort_values(by="Resultado Total (USD)", ascending=False)
        st.dataframe(df_final, use_container_width=True)

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



