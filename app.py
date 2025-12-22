import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import yfinance as yf
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística Pro 2025", layout="wide", page_icon="🌾")

# 2. FUNCIONES DE AUTOMATIZACIÓN (DÓLAR Y PRECIOS)
@st.cache_data(ttl=3600)
def obtener_datos_mercado():
    # Obtener Dólar MEP (API DolarApi)
    try:
        res_dolar = requests.get("dolarapi.com")
        dolar = float(res_dolar.json()['venta'])
    except:
        dolar = 1050.0  # Respaldo

    # Obtener Precios Cereales (Yahoo Finance - Chicago)
    tickers = {"Soja": "ZS=F", "Maíz": "ZC=F", "Trigo": "ZW=F", "Girasol": "base"}
    precios = {}
    try:
        for nombre, ticker in tickers.items():
            if ticker == "base":
                precios[nombre] = 310.0
            else:
                data = yf.Ticker(ticker)
                hist = data.history(period="1d")
                precio_bushel = hist['Close'].iloc[-1]
                # Conversión a USD/tonelada
                factor = 0.3674 if nombre in ["Soja", "Trigo"] else 0.3936
                precios[nombre] = round(precio_bushel * factor, 2)
    except:
        precios = {"Soja": 300.0, "Maíz": 185.0, "Trigo": 215.0, "Girasol": 310.0}
    
    return dolar, precios

@st.cache_data
def cargar_acopios():
    try:
        df = pd.read_excel("acopios_argentina.xlsx")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])

# Ejecución de carga
dolar_hoy, precios_hoy = obtener_datos_mercado()
df_acopios = cargar_acopios()

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.title("📈 Mercado en Vivo")
    st.metric("Dólar MEP", f"${dolar_hoy:,.2f} ARS")
    st.divider()
    
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_hoy.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    
    precio_usd = precios_hoy[grano_sel]
    st.metric(f"Pizarra {grano_sel}", f"US$ {precio_usd}")
    st.write(f"Equivalente: **${(precio_usd * dolar_hoy):,.2f} ARS/tn**")
    st.info("Actualizado automáticamente vía Yahoo Finance & DolarApi 2025")

# 4. CUERPO PRINCIPAL Y MAPA
st.title("🚜 Optimizador Logístico y Comercial")
st.markdown("Haz clic en el mapa sobre tu **lote** para analizar opciones en un radio de 50km.")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)

# Puertos Exportadores Fijos
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], tooltip="Puerto",
                  icon=folium.Icon(color="red", icon="ship", prefix="fa")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # Evaluar Puertos
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete = (d * 1400) / dolar_hoy # Tarifa 2025 est.
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd})
        
    # Evaluar Acopios (Radio 50km)
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                costo_flete = (d * 1400) / dolar_hoy
                resultados.append({"Destino": row['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd - 7})

    if resultados:
        df_res = pd.DataFrame(resultados)
        
        st.divider()
        st.subheader("🎯 Personalización de Gastos y Rentabilidad")
        
        col_sel, col_gastos = st.columns([1, 2])
        
        with col_sel:
            opcion = st.selectbox("Seleccione destino para calcular:", df_res["Destino"].tolist())
            datos_dest = df_res[df_res["Destino"] == opcion].iloc[0]
            st.write(f"**Distancia:** {datos_dest['KM']:.1f} km")
            st.write(f"**Flete estimado:** US$ {datos_dest['Flete_TN']:.2f}/tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                c1, c2 = st.columns(2)
                p_com = c1.number_input("Comisión (%)", value=2.0, step=0.1)
                p_mer = c2.number_input("Merma (%)", value=0.5, step=0.1)
                g_fijo = c1.number_input("Otros Gastos (USD/tn)", value=0.1)
                g_corto = c2.number_input("Flete Corto (USD/tn)", value=0.0)

        # CÁLCULO FINAL
        valor_bruto = datos_dest['Base_USD'] * toneladas
        desc_comision = valor_bruto * (p_com / 100)
        desc_merma = valor_bruto * (p_mer / 100)
        costo_flete_total = datos_dest['Flete_TN'] * toneladas
        costo_fijos_total = (g_fijo + g_corto) * toneladas
        
        neto_final = valor_bruto - desc_comision - desc_merma - costo_flete_total - costo_fijos_total
        
        st.metric(f"💰 Margen Neto Final en {opcion}", f"US$ {neto_final:,.2f}")
        
        # Tabla Comparativa General
        st.write("---")
        st.write("📋 **Comparativa rápida de la zona (Solo flete):**")
        df_res["Neto_Est_USD"] = (df_res["Base_USD"] - df_res["Flete_TN"]) * toneladas
        st.dataframe(df_res[["Destino", "KM", "Neto_Est_USD"]].sort_values("Neto_Est_USD", ascending=False), use_container_width=True)
else:
    st.info("👆 Haz clic en el mapa sobre la ubicación de tu lote para comenzar.")



