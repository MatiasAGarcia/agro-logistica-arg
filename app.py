import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística BCR 2025", layout="wide", page_icon="🌾")

# 2. FUNCIONES DE MERCADO (DÓLAR BNA DIVISA Y PIZARRA BCR)
@st.cache_data(ttl=3600)
def obtener_datos_mercado_argentino():
    try:
        res_dolar = requests.get("dolarapi.com")
        dolar = float(res_dolar.json()['venta'])
    except:
        dolar = 1450.0  # Referencia BNA Dic 2025

    try:
        pizarras_ars = {
            "Soja": 494000.0,
            "Maíz": 275400.0,
            "Trigo": 252350.0,
            "Girasol": 497500.0
        }
        precios_usd = {k: round(v / dolar, 2) for k, v in pizarras_ars.items()}
    except:
        precios_usd = {"Soja": 340.69, "Maíz": 189.93, "Trigo": 174.03, "Girasol": 343.10}
    
    return dolar, precios_usd

@st.cache_data
def cargar_acopios():
    try:
        df = pd.read_excel("acopios_argentina.xlsx")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])

dolar_bna, precios_pizarra = obtener_datos_mercado_argentino()
df_acopios = cargar_acopios()

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.title("📈 Monitor BCR / BNA")
    st.metric("Dólar Divisa BNA", f"${dolar_bna:,.2f} ARS")
    st.divider()
    
    st.header("⚙️ Parámetros de Carga")
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_pizarra.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    
    st.divider()
    st.header("🚛 Tarifas de Transporte")
    # Tarifa manual por KM (Referencia CATAC/FADEEAC)
    tarifa_km_ars = st.number_input("Tarifa Flete Largo (ARS/KM)", value=1400, step=50)
    
    st.divider()
    precio_usd = precios_pizarra[grano_sel]
    st.metric(f"Pizarra {grano_sel} (BCR)", f"US$ {precio_usd}")

# 4. CUERPO PRINCIPAL Y MAPA
st.title("🚜 Optimizador Logístico y Comercial")
st.markdown("Haz clic en el mapa sobre tu **lote** para analizar opciones.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], 
                  icon=folium.Icon(color="red", icon="ship", prefix="fa")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # Cálculo dinámico usando la tarifa manual de la barra lateral
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete_largo = (d * tarifa_km_ars) / dolar_bna 
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_Largo_TN": costo_flete_largo, "Base_USD": precio_usd})
        
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                costo_flete_largo = (d * tarifa_km_ars) / dolar_bna
                resultados.append({"Destino": row['nombre'], "KM": d, "Flete_Largo_TN": costo_flete_largo, "Base_USD": precio_usd - 7.0})

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.divider()
        
        col_sel, col_gastos = st.columns(2)
        
        with col_sel:
            opcion = st.selectbox("Seleccione destino para detallar:", df_res["Destino"].tolist())
            datos_dest = df_res[df_res["Destino"] == opcion].iloc
            st.write(f"**Distancia Calculada:** {datos_dest['KM']:.1f} km")
            st.write(f"**Flete Largo (Auto):** US$ {datos_dest['Flete_Largo_TN']:.2f} /tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                c1, c2 = st.columns(2)
                p_comision = c1.number_input("Comisión (%)", value=2.0, step=0.1)
                p_merma = c2.number_input("Merma (%)", value=0.5, step=0.1)
                
                st.write("**Gastos Fijos (USD/tn)**")
                g_flete_corto = c1.number_input("Flete Corto (Manual)", value=0.0)
                g_laboratorio = c2.number_input("Laboratorio", value=0.1)
                g_paritarias = c1.number_input("Paritarias", value=0.0)
                g_otros = c2.number_input("Otros Gastos", value=0.0)

        # CÁLCULO FINAL
        v_bruto_total = datos_dest['Base_USD'] * toneladas
        desc_porcentual = v_bruto_total * ((p_comision + p_merma) / 100)
        
        # Gastos fijos: El Flete Largo se suma a los manuales
        gastos_tn = datos_dest['Flete_Largo_TN'] + g_flete_corto + g_laboratorio + g_paritarias + g_otros
        desc_fijos_total = gastos_tn * toneladas
        
        neto_final = v_bruto_total - desc_porcentual - desc_fijos_total
        
        st.metric(f"💰 Margen Neto Final en {opcion}", f"US$ {neto_final:,.2f}")
        
        with st.expander("Ver detalle del cálculo"):
            st.write(f"Valor Bruto: US$ {v_bruto_total:,.2f}")
            st.write(f"Gastos Com. y Merma: - US$ {desc_porcentual:,.2f}")
            st.write(f"Logística y Otros: - US$ {desc_fijos_total:,.2f}")
