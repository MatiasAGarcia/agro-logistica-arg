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
    # Obtener Dólar DIVISA VENDEDOR BNA
    try:
        res_dolar = requests.get("dolarapi.com")
        dolar = float(res_dolar.json()['venta'])
    except:
        dolar = 1450.0  # Referencia BNA Dic 2025

    # Precios Pizarra BCR (Referencia Rosario en Pesos)
    try:
        pizarras_ars = {
            "Soja": 494000.0,
            "Maíz": 275400.0,
            "Trigo": 252350.0,
            "Girasol": 497500.0
        }
        # Conversión a USD
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
    st.caption("Referencia oficial Banco Nación")
    st.divider()
    
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_pizarra.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    
    precio_usd = precios_pizarra[grano_sel]
    st.metric(f"Pizarra {grano_sel} (BCR)", f"US$ {precio_usd}")
    st.write(f"Valor en pesos: **${(precio_usd * dolar_bna):,.0f} ARS/tn**")

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

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # Evaluar Puertos
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        costo_flete = (d * 1400) / dolar_bna 
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd})
        
    # Evaluar Acopios Cercanos
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                costo_flete = (d * 1400) / dolar_bna
                resultados.append({"Destino": row['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd - 7.0})

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.divider()
        
        # CORRECCIÓN AQUÍ: Se especifica el número de columnas (2)
        col_sel, col_gastos = st.columns(2)
        
        with col_sel:
            opcion = st.selectbox("Seleccione destino para detallar:", df_res["Destino"].tolist())
            # CORRECCIÓN AQUÍ: Acceso seguro a la fila
            datos_dest = df_res[df_res["Destino"] == opcion].iloc[0]
            st.write(f"**Distancia:** {datos_dest['KM']:.1f} km")
            st.write(f"**Costo flete:** US$ {datos_dest['Flete_TN']:.2f} /tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                p_com = st.number_input("Comisión (%)", value=2.0, step=0.1)
                p_mer = st.number_input("Merma (%)", value=0.5, step=0.1)
                g_fijo = st.number_input("Otros Gastos (USD/tn)", value=0.1)

        # Cálculo Final
        v_bruto = datos_dest['Base_USD'] * toneladas
        desc_porc = v_bruto * ((p_com + p_mer) / 100)
        flete_t = datos_dest['Flete_TN'] * toneladas
        otros_t = g_fijo * toneladas
        neto_f = v_bruto - desc_porc - flete_t - otros_t
        
        st.metric(f"💰 Margen Neto Final en {opcion}", f"US$ {neto_f:,.2f}")
        
        # Tabla Comparativa Rápida
        st.write("---")
        st.subheader("📋 Comparativa Regional (Pizarra - Flete)")
        df_res["Neto_Est_USD"] = (df_res["Base_USD"] - df_res["Flete_TN"]) * toneladas
        st.dataframe(df_res[["Destino", "KM", "Neto_Est_USD"]].sort_values("Neto_Est_USD", ascending=False), use_container_width=True)
else:
    st.info("👆 Haz clic en el mapa sobre tu lote para comenzar.")


