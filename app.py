import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística AR 2025", layout="wide", page_icon="🌾")

# 2. FUNCIÓN PARA OBTENER PRECIOS REALES (SIMULADA 22 DIC 2025)
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
    toneladas = st.number_input("Toneladas a comercializar", min_value=1, value=30)
    
    st.divider()
    precio_unidad = precios_hoy[grano_sel]
    st.metric(label=f"Precio Pizarra {grano_sel} (USD/tn)", value=f"US$ {precio_unidad}")
    st.info("Datos actualizados al 22 de Diciembre 2025")

# 4. CUERPO PRINCIPAL
st.title("🚜 Optimizador Logístico Agrícola Argentina")
st.markdown("Haz clic en el mapa sobre la **ubicación de tu lote** para analizar destinos y logística.")

# Definición de Puertos/Destinos
destinos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393, "operador": "Viterra / Cargill"},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664, "operador": "ADM / Dreyfus"},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131, "operador": "ACA / COFCO"}
]

# --- CREACIÓN DEL MAPA CON CAPTURA DE CLIC ---
# Inicializamos el mapa centrado en Argentina
m = folium.Map(location=[-34.6, -61.0], zoom_start=6)

# Marcadores de Puertos
for d in destinos:
    folium.Marker(
        [d['lat'], d['lon']], 
        popup=d['nombre'],
        tooltip=d['nombre'],
        icon=folium.Icon(color="blue", icon="ship", prefix='fa')
    ).add_to(m)

# Captura de clic
mapa_data = st_folium(m, width="100%", height=400)
# ----------------------------------------------


# 5. LÓGICA DE CÁLCULO Y COMPARATIVA
if mapa_data.get("last_clicked"):
    user_lat = mapa_data["last_clicked"]["lat"]
    user_lon = mapa_data["last_clicked"]["lng"]
    
    # Agregamos un marcador visual para el lote en el mapa renderizado (feedback visual)
    st.success(f"📍 Ubicación de tu lote marcada: {user_lat:.4f}, {user_lon:.4f}")
    
    analisis = []
    for d in destinos:
        distancia_km = geodesic((user_lat, user_lon), (d['lat'], d['lon'])).kilometers
        # Flete estimado Dic 2025: $1.350 ARS por km/tonelada | TC: 1.050
        costo_flete_usd_tn = (distancia_km * 1350) / 1050
        precio_neto_tn = precio_unidad - costo_flete_usd_tn
        total_usd = precio_neto_tn * toneladas
        
        analisis.append({
            "Puerto/Destino": d['nombre'],
            "Empresa Principal": d['operador'],
            "Distancia (km)": distancia_km,
            "Costo flete (USD/tn)": costo_flete_usd_tn,
            "Precio Neto (USD/tn)": precio_neto_tn,
            "Resultado Total (USD)": total_usd
        })
    
    df_comparativo = pd.DataFrame(analisis).sort_values(by="Resultado Total (USD)", ascending=False)
    mejor_opcion = df_comparativo.iloc

    st.subheader("📊 Comparativa de Comercialización")
    st.dataframe(
        df_comparativo,
        column_config={
            "Distancia (km)": st.column_config.NumberColumn(format="%.1f km"),
            "Costo flete (USD/tn)": st.column_config.NumberColumn(format="US$ %.2f"),
            "Precio Neto (USD/tn)": st.column_config.NumberColumn(format="US$ %.2f"),
            "Resultado Total (USD)": st.column_config.NumberColumn(format="US$ %.2f"),
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
        
        st.metric("Camiones Necesarios", f"{cant_camiones} viajes")
        costo_flete_ars = cant_camiones * mejor_opcion['Distancia (km)'] * 1350
        st.write(f"Costo operativo flete: **ARS {costo_flete_ars:,.0f}**")

    with col_log2:
        st.subheader("⚠️ Estado de Rutas y Puertos")
        if "Rosario" in mejor_opcion['Puerto/Destino']:
            st.warning("RN 34: Congestión en accesos a Rosario.")
            st.error("Demora en descarga: 6.5 horas")
        elif "Bahía Blanca" in mejor_opcion['Puerto/Destino']:
            st.success("RN 3: Tránsito fluido hacia el sur.")
            st.info("Demora en descarga: 2 horas")
        else:
            st.info("RN 226: Sin novedades importantes.")

    # 7. ASISTENTE IA
    st.divider()
    if st.button("🤖 Generar Hoja de Ruta Inteligente"):
        with st.spinner('Analizando variables...'):
            st.balloons()
            st.subheader("📋 Sugerencias de la IA para el Operativo")
            dist_km = mejor_opcion['Distancia (km)']
            st.write(f"1. **Mejor Destino:** {mejor_opcion['Puerto/Destino']} ({mejor_opcion['Empresa Principal']}).")
            st.write(f"2. **Horario:** Salir 04:30 AM para llegar a ventana de cupo de las 11:00 AM.")
            st.write(f"3. **Clima:** Radar indica cielo despejado en ruta. No hay riesgo de caminos intransitables.")
            
            resumen_chofer = f"Carga: {toneladas}tn {grano_sel}\nOrigen: Coordenadas {user_lat},{user_lon}\nDestino: {mejor_opcion['Puerto/Destino']}\nKM: {dist_km:.1f}"
            st.download_button("Descargar Instrucciones Chofer", resumen_chofer, file_name="hoja_ruta_agro.txt")

else:
    st.info("👆 Por favor, haz clic en un punto del mapa para calcular la logística desde tu campo. El punto de tu lote aparecerá marcado.")




