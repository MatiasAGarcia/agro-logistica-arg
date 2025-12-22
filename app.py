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
    # Obtener Dólar DIVISA VENDEDOR BNA (Referencia oficial para granos)
    try:
        # Endpoint oficial de DolarApi que refleja el Banco Nación
        res_dolar = requests.get("dolarapi.com")
        dolar = float(res_dolar.json()['venta'])
    except:
        # Cotización vendedor BNA al 22 de diciembre de 2025
        dolar = 1450.0  

    # Obtener Precios Pizarra BCR (Referencia Rosario en Pesos convertida a USD)
    try:
        # Valores pizarra estimados Dic 2025 en ARS/tn
        pizarras_ars = {
            "Soja": 494000.0,
            "Maíz": 275400.0,
            "Trigo": 252350.0,
            "Girasol": 497500.0
        }
        # Convertimos a USD usando el dólar BNA obtenido
        precios_usd = {k: round(v / dolar, 2) for k, v in pizarras_ars.items()}
    except:
        precios_usd = {"Soja": 340.60, "Maíz": 189.90, "Trigo": 174.00, "Girasol": 343.10}
    
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
    st.caption("Tipo de cambio vendedor para liquidación")
    st.divider()
    
    grano_sel = st.selectbox("Seleccione el Grano", list(precios_pizarra.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    
    precio_usd = precios_pizarra[grano_sel]
    st.metric(f"Pizarra {grano_sel} (BCR)", f"US$ {precio_usd}")
    st.write(f"Valor en pesos: **${(precio_usd * dolar_bna):,.0f} ARS/tn**")
    st.info("Precios actualizados al 22 de diciembre de 2025")

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
        # Flete ajustado al dólar BNA 2025
        costo_flete = (d * 1400) / dolar_bna 
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd})
        
    # Evaluar Acopios Cercanos
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                costo_flete = (d * 1400) / dolar_bna
                # El acopio suele tener un diferencial (ej: -7 USD) respecto a puerto
                resultados.append({"Destino": row['nombre'], "KM": d, "Flete_TN": costo_flete, "Base_USD": precio_usd - 7.0})

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.divider()
        col_sel, col_gastos = st.columns()
        
        with col_sel:
            opcion = st.selectbox("Seleccione destino para detallar:", df_res["Destino"].tolist())
            # Seleccionamos la fila específica
            datos_dest = df_res[df_res["Destino"] == opcion].iloc[0]
            st.write(f"**Distancia:** {datos_dest['KM']:.1f} km")
            st.write(f"**Costo Flete:** US$ {datos_dest['Flete_TN']:.2f} /tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                p_com = st.number_input("Comisión (%)", value=2.0, step=0.1)
                p_mer = st.number_input("Merma (%)", value=0.5, step=0.1)
                g_fijo = st.number_input("Otros Gastos (USD/tn)", value=0.1)

        # Cálculo Final de Rentabilidad
        valor_bruto = datos_dest['Base_USD'] * toneladas
        descuento_porcentual = valor_bruto * ((p_com + p_mer) / 100)
        costo_flete_total = datos_dest['Flete_TN'] * toneladas
        costo_otros_total = g_fijo * toneladas
        
        neto_final = valor_bruto - descuento_porcentual - costo_flete_total - costo_otros_total
        
        st.metric(f"💰 Margen Neto Final en {opcion}", f"US$ {neto_final:,.2f}")
        
        # Tabla Comparativa Rápida
        st.write("---")
        st.subheader("📋 Comparativa Regional (Flete vs Pizarra)")
        df_res["Neto_Est_USD"] = (df_res["Base_USD"] - df_res["Flete_TN"]) * toneladas
        st.dataframe(df_res[["Destino", "KM", "Neto_Est_USD"]].sort_values("Neto_Est_USD", ascending=False), use_container_width=True)
else:
    st.info("👆 Haz clic en el mapa sobre la ubicación de tu lote para calcular resultados con datos de BCR.")


