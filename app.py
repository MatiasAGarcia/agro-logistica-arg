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
        df = pd.read_excel("acopios_argentina.xlsx", engine='openpyxl')
        df.columns = df.columns.str.strip().str.lower()
        df = df.dropna(subset=['lat', 'lon', 'nombre'])
        return df
    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
        return pd.DataFrame(columns=["nombre", "lat", "lon", "tipo"])

dolar_bna, precios_pizarra = obtener_datos_mercado_argentino()
df_acopios = cargar_acopios()

# --- FUNCIÓN DE REPORTE PDF ---
def generar_pdf(datos_finales, opcion_nombre, neto_final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Comercializacion AgroLogistica BCR", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Fecha: 23 de Diciembre de 2025 | Destino: {opcion_nombre}", ln=True, align="C")
    pdf.ln(10)
    for key, value in datos_finales.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, txt=f"MARGEN NETO FINAL ESTIMADO: US$ {neto_final:,.2f}", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')

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
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], icon=folium.Icon(color="red", icon="ship", prefix="fa")).add_to(m)
mapa_data = st_folium(m, width="100%", height=400)

# 5. LÓGICA DE CÁLCULO
if mapa_data.get("last_clicked"):
    u_lat, u_lon = mapa_data["last_clicked"]["lat"], mapa_data["last_clicked"]["lng"]
    resultados = []
    
    # CORRECCIÓN DE FÓRMULA: Costo de 1KM en USD/TN
    costo_un_km_usd_tn = (tarifa_km_ars / dolar_bna) / toneladas

    for p in puertos:
        d = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).kilometers
        flete_largo_usd_tn = d * costo_un_km_usd_tn
        resultados.append({"Destino": p['nombre'], "KM": d, "Flete_Largo_TN": flete_largo_usd_tn, "Base_USD": precio_usd_base})
        
    if not df_acopios.empty:
        for _, row in df_acopios.iterrows():
            d = geodesic((u_lat, u_lon), (row['lat'], row['lon'])).kilometers
            if d <= 50:
                flete_largo_usd_tn = d * costo_un_km_usd_tn
                resultados.append({"Destino": row['nombre'], "KM": d, "Flete_Largo_TN": flete_largo_usd_tn, "Base_USD": precio_usd_base - 7.0})

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.divider()
        col_sel, col_gastos = st.columns(2)
        
        with col_sel:
            opcion_nombre = st.selectbox("Seleccione destino para detallar:", df_res["Destino"].tolist())
            datos_dest = df_res[df_res["Destino"] == opcion_nombre].iloc[0].to_dict()
            
            st.write(f"**Distancia Calculada:** {datos_dest['KM']:.1f} km")
            st.write(f"**Flete Largo Est.:** US$ {datos_dest['Flete_Largo_TN']:.2f} /tn")

        with col_gastos:
            with st.expander("🛠️ Ajustar Gastos Manuales", expanded=True):
                c1, c2 = st.columns(2)
                p_comision = c1.number_input("Comisión (%)", value=2.0, step=0.1)
                p_merma = c2.number_input("Merma (%)", value=0.5, step=0.1)
                st.write("**Gastos Fijos (USD/tn)**")
                g_flete_corto = c1.number_input("Flete Corto", value=0.0)
                g_laboratorio = c2.number_input("Laboratorio", value=0.1)
                g_paritarias = c1.number_input("Paritarias", value=0.0)
                g_otros = c2.number_input("Otros Gastos", value=0.0)

        # CÁLCULO FINAL
        v_bruto_total = datos_dest['Base_USD'] * toneladas
        desc_porcentual = v_bruto_total * ((p_comision + p_merma) / 100)
        gastos_fijos_tn = datos_dest['Flete_Largo_TN'] + g_flete_corto + g_laboratorio + g_paritarias + g_otros
        desc_fijos_total = gastos_fijos_tn * toneladas
        neto_final = v_bruto_total - desc_porcentual - desc_fijos_total
        
        st.metric(f"💰 Margen Neto Final en {opcion_nombre}", f"US$ {neto_final:,.2f}")
        
        # Botón de descarga PDF
        datos_reporte = {
            "Cereal": grano_sel, "Toneladas": toneladas, "Destino": opcion_nombre,
            "Margen Neto Total": f"US$ {neto_final:,.2f}", 
            "Precio Pizarra": f"US$ {precio_usd_base}", "Dolar BNA": f"${dolar_bna}"
        }
        pdf_bytes = generar_pdf(datos_reporte, opcion_nombre, neto_final)
        
        st.download_button(
            label="Descargar Reporte Profesional (PDF)",
            data=pdf_bytes,
            file_name="Reporte_AgroLogistica_BCR.pdf",
            mime="application/pdf"
        )
