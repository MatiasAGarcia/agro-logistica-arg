import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests
from fpdf import FPDF

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="AgroLogística BCR 2025", layout="wide", page_icon="🌾")

# 2. FUNCIONES DE MERCADO (DÓLAR BNA Y PIZARRA BCR)
@st.cache_data(ttl=3600)
def obtener_datos_mercado_argentino():
    try:
        # Dólar Divisa Vendedor BNA
        res_dolar = requests.get("dolarapi.com")
        dolar = float(res_dolar.json()['venta'])
    except:
        dolar = 1450.0  # Referencia BNA al 25 de Dic 2025

    try:
        # Precios Pizarra BCR en ARS/tn (Referencia Rosario)
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
        df = pd.read_excel("acopios_argentina.xlsx", engine='openpyxl')
        df.columns = df.columns.str.strip().str.lower()
        return df.dropna(subset=['lat', 'lon', 'nombre'])
    except:
        return pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])

dolar_bna, precios_pizarra = obtener_datos_mercado_argentino()
df_acopios = cargar_acopios()

# --- FUNCIÓN DE REPORTE PDF ---
def generar_pdf(datos_reporte, opcion_nombre, neto_final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Comercializacion AgroLogistica BCR", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Destino: {opcion_nombre}", ln=True, align="C")
    pdf.ln(10)
    for key, value in datos_reporte.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, txt=f"MARGEN NETO FINAL: US$ {neto_final:,.2f}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# 3. INTERFAZ LATERAL
with st.sidebar:
    st.title("📈 Monitor BCR / BNA")
    st.metric("Dólar Divisa BNA", f"${dolar_bna:,.2f} ARS")
    st.divider()
    
    st.header("⚙️ Parámetros de Carga")
    grano_sel = st.selectbox("Grano", list(precios_pizarra.keys()))
    toneladas = st.number_input("Toneladas totales", min_value=1.0, value=30.0)
    
    st.divider()
    st.header("🚛 Tarifa de Transporte")
    # Tarifa de referencia en ARS/TN
    tarifa_referencia_ars = st.number_input("Tarifa de Referencia (ARS/TN)", value=26550.0, step=100.0)
    
    # CÁLCULO SOLICITADO: ARS/TN dividido Dólar BNA
    flete_largo_usd_tn = tarifa_referencia_ars / dolar_bna
    st.metric("Flete Largo Est. (USD/TN)", f"US$ {flete_largo_usd_tn:.2f}")
    
    st.divider()
    precio_usd_base = precios_pizarra[grano_sel]
    st.metric(f"Pizarra {grano_sel} (BCR)", f"US$ {precio_usd_base}")

# 4. CUERPO PRINCIPAL Y MAPA
st.title("🚜 Optimizador Logístico y Comercial")
st.markdown("Haz clic en el mapa para analizar destinos (radio 50km para acopios).")

m = folium.Map(location=[-34.0, -61.0], zoom_start=7)
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.9468, "lon": -60.6393},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.7183, "lon": -62.2664},
    {"nombre": "Puerto Quequén", "lat": -38.5858, "lon": -58.7131}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], icon=folium.Icon(color="red", icon="ship", prefix="fa")).add_to(m)

mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_USD_TN": flete_largo_usd_tn, "Base_USD": precio_usd_base})
        
    for _, row in df_acopios.iterrows():
        d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
        if d <= 50:
            resultados.append({"Destino": row['nombre'], "KM": d, "Flete_USD_TN": flete_largo_usd_tn, "Base_USD": precio_usd_base - 7.0})

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.divider()
        col_sel, col_gastos = st.columns(2)
        
        with col_sel:
            opcion = st.selectbox("Seleccione destino:", df_res["Destino"].tolist())
            # Acceso seguro a la fila y conversión a diccionario
            datos_dest = df_res[df_res["Destino"] == opcion].iloc[0].to_dict()
            st.write(f"**Distancia:** {datos_dest['KM']:.1f} km")
            st.write(f"**Costo Flete:** US$ {datos_dest['Flete_USD_TN']:.2f} /tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                c1, c2 = st.columns(2)
                p_com = c1.number_input("Comisión (%)", value=2.0)
                p_mer = c2.number_input("Merma (%)", value=0.5)
                g_lab = c1.number_input("Laboratorio (USD/tn)", value=0.1)
                g_par = c2.number_input("Paritarias (USD/tn)", value=0.0)
                g_corto = c1.number_input("Flete Corto (USD/tn)", value=0.0)

        # CÁLCULO FINAL CORREGIDO
        valor_bruto = datos_dest['Base_USD'] * toneladas
        desc_porc = valor_bruto * ((p_com + p_mer) / 100)
        
        # Gastos fijos por tonelada (incluye el flete largo calculado)
        gastos_fijos_usd_tn = datos_dest['Flete_USD_TN'] + g_lab + g_par + g_corto
        total_gastos_fijos = gastos_fijos_usd_tn * toneladas
        
        neto_final = valor_bruto - desc_porc - total_gastos_fijos
        
        st.metric(f"💰 Margen Neto Final en {opcion}", f"US$ {neto_final:,.2f}")
        
        # Botón PDF
        reporte = {"Cereal": grano_sel, "TN": toneladas, "Flete USD/TN": round(datos_dest['Flete_USD_TN'], 2)}
        pdf_bytes = generar_pdf(reporte, opcion, neto_final)
        st.download_button("Descargar PDF", pdf_bytes, "reporte_agro.pdf")
