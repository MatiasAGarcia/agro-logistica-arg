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

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.header("⚙️ Parámetros Generales")
    grano_sel = st.selectbox("Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    precio_base = precios_hoy[grano_sel]
    st.metric(f"Pizarra {grano_sel}", f"USD {precio_base}")

# 4. MAPA
st.title("🌾 Calculador Logístico con Gastos Porcentuales")
st.markdown("Haz clic en el mapa y luego personaliza los gastos de comercialización.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], icon=folium.Icon(color="red")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete = (d * 1350) / 1050
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_TN": costo_flete, "Precio_B": precio_base})
        
    for _, row in df_acopios.iterrows():
        d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
        if d <= 50:
            costo_flete = (d * 1350) / 1050
            resultados.append({"Destino": row['nombre'], "KM": d, "Flete_TN": costo_flete, "Precio_B": precio_base - 7})

    if resultados:
        df_res = pd.DataFrame(resultados)
        
        st.divider()
        st.subheader("🎯 Personalización de Gastos por Destino")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            destino_elegido = st.selectbox("Seleccione destino:", df_res["Destino"].tolist())
            datos_dest = df_res[df_res["Destino"] == destino_elegido].iloc[0]
            
            valor_bruto_total = precio_base * toneladas
            st.write(f"**Valor Bruto:** US$ {valor_bruto_total:,.2f}")

        with col2:
            expander = st.expander("🛠️ Cargar Gastos (Fijos y Porcentuales)", expanded=True)
            with expander:
                c1, c2 = st.columns(2)
                # Gastos en Porcentaje (%)
                porc_comision = c1.number_input("Comisión (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
                porc_merma = c2.number_input("Merma Volátil (%)", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
                
                # Gastos en USD por Tonelada
                g_par = c1.number_input("Paritarias (USD/tn)", value=0.0)
                g_lab = c2.number_input("Laboratorio (USD/tn)", value=0.1)
                g_fcorto = c1.number_input("Flete Corto (USD/tn)", value=0.0)
                g_otros = c2.number_input("Otros (USD/tn)", value=0.0)

        # --- CÁLCULOS FINALES CON PORCENTAJES ---
        # 1. Gastos porcentuales sobre el valor bruto
        monto_comision = valor_bruto_total * (porc_comision / 100)
        monto_merma = valor_bruto_total * (porc_merma / 100)
        
        # 2. Gastos fijos por tonelada
        total_gastos_fijos_tn = g_par + g_lab + g_fcorto + g_otros + datos_dest['Flete_TN']
        monto_gastos_fijos = total_gastos_fijos_tn * toneladas
        
        # 3. Neto Final
        neto_total_usd = valor_bruto_total - monto_comision - monto_merma - monto_gastos_fijos
        neto_por_tn = neto_total_usd / toneladas
        
        # Mostrar Resultados
        st.metric(f"💰 Resultado Neto Final en {destino_elegido}", f"US$ {neto_total_usd:,.2f}")
        
        st.write("---")
        det_col1, det_col2 = st.columns(2)
        det_col1.write(f"📉 **Descuento Comisión ({porc_comision}%):** US$ {monto_comision:,.2f}")
        det_col1.write(f"📉 **Descuento Merma ({porc_merma}%):** US$ {monto_merma:,.2f}")
        det_col2.write(f"🚚 **Costo Flete Total:** US$ {datos_dest['Flete_TN']*toneladas:,.2f}")
        det_col2.write(f"💵 **Neto por Tonelada:** US$ {neto_por_tn:,.2f}")


