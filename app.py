import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests
from fpdf import FPDF

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
            "Soja": 494000.0, "Maíz": 275400.0, "Trigo": 252350.0, "Girasol": 497500.0
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
    tarifa_km_ars = st.number_input("Tarifa Flete Largo (ARS/KM)", value=1400.0, step=50.0)
    # Conversión informativa de la tarifa a USD/KM
    tarifa_usd_km = tarifa_km_ars / dolar_bna
    st.caption(f"Equivalente a: US$ {tarifa_usd_km:.4f} por KM")
    
    st.divider()
    precio_usd_base = precios_pizarra[grano_sel]
    st.metric(f"Pizarra {grano_sel} (BCR)", f"US$ {precio_usd_base}")

# 4. CUERPO PRINCIPAL Y MAPA
st.title("🚜 Optimizador Logístico y Comercial")
st.markdown("Haz clic en el mapa sobre tu **lote** para analizar destinos.")

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

# --- DENTRO DE LA LÓGICA DE CÁLCULO (Paso 5) ---
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # 1. Calcular el valor de 1 KM en Dólares por Tonelada
    # Si la tarifa es ARS por KM para un camión, la dividimos por el dólar y por las toneladas
    costo_un_km_usd_tn = (tarifa_km_ars / dolar_bna) / toneladas

    # Evaluar Puertos
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        # Flete largo por tonelada = Distancia * Costo de 1 KM en USD/TN
        flete_largo_usd_tn = d * costo_un_km_usd_tn
        
        resultados.append({
            "Destino": p['nombre'], 
            "KM": d, 
            "Flete_Largo_TN": flete_largo_usd_tn, 
            "Base_USD": precio_usd_base
        })
        
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                flete_largo_usd_tn = d * costo_un_km_usd_tn
                # Acopios suelen tener una base menor que el puerto
                resultados.append({
                    "Destino": row['nombre'], 
                    "KM": d, 
                    "Flete_Largo_TN": flete_largo_usd_tn, 
                    "Base_USD": precio_usd_base - 7.0
                })

   
        # CÁLCULO FINAL (Consistente con la rentabilidad por lote)
        v_bruto_total = datos_dest['Base_USD'] * toneladas
        desc_porcentual = v_bruto_total * ((p_comision + p_merma) / 100)
        
        # Gastos fijos por tonelada (incluye el flete largo ya convertido)
        gastos_fijos_tn = datos_dest['Flete_Largo_TN'] + g_flete_corto + g_laboratorio + g_paritarias + g_otros
        desc_fijos_total = gastos_fijos_tn * toneladas
        
        neto_final = v_bruto_total - desc_porcentual - desc_fijos_total
        
        st.metric(f"💰 Margen Neto Final en {opcion_nombre}", f"US$ {neto_final:,.2f}")
        st.caption(f"Resultado por tonelada: US$ {neto_final/toneladas:.2f}")




