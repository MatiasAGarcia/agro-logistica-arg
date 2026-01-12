import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import requests
from fpdf import FPDF

# 1. CONFIGURACIÓN
st.set_page_config(page_title="AgroLogística BCR 2026", layout="wide", page_icon="🌾")

@st.cache_data(ttl=3600)
def obtener_datos_mercado():
    # En 2026 usamos APIs robustas para el mercado argentino
    try:
        res = requests.get("dolarapi.com", timeout=5)
        dolar = float(res.json()['venta'])
    except:
        dolar = 1150.0  # Referencia estimada
    
    precios_usd = {"Soja": 320.0, "Maíz": 175.0, "Trigo": 190.0, "Girasol": 310.0}
    return dolar, precios_usd

@st.cache_data
def cargar_acopios():
    # Simulación de carga; asegúrate de tener tu archivo excel con columnas 'lat', 'lon', 'nombre'
    try:
        df = pd.read_excel("acopios_argentina.xlsx")
        return df.dropna(subset=['lat', 'lon', 'nombre'])
    except:
        # Datos de prueba si no existe el archivo
        return pd.DataFrame([
            {"nombre": "Acopio Norte", "lat": -33.12, "lon": -60.95, "tipo": "Cooperativa"},
            {"nombre": "Planta General", "lat": -34.05, "lon": -61.20, "tipo": "Privado"}
        ])

dolar_bna, precios_pizarra = obtener_datos_mercado()
df_acopios = cargar_acopios()

# --- FUNCIÓN PDF CON DESGLOSE ---
def generar_pdf_detalle(info_calculo, destino_nombre, neto_final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Liquidación Estimada de Comercialización", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Destino: {destino_nombre}", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    # Tabla de desglose
    pdf.cell(100, 10, "Concepto", border=1)
    pdf.cell(45, 10, "Cálculo", border=1)
    pdf.cell(45, 10, "Total (USD)", border=1, ln=True)

    conceptos = [
        ("Valor Bruto", f"{info_calculo['tn']} tn x ${info_calculo['precio_base']}", f"{info_calculo['bruto']:,.2f}"),
        ("Gastos % (Com+Mer)", f"{info_calculo['perc_gasto']}%", f"-{info_calculo['desc_perc']:,.2f}"),
        ("Flete Largo", f"${info_calculo['flete_tn']}/tn", f"-{info_calculo['total_flete']:,.2f}"),
        ("Otros Gastos Fijos", f"${info_calculo['otros_tn']}/tn", f"-{info_calculo['total_otros']:,.2f}"),
    ]

    for c, calc, tot in conceptos:
        pdf.cell(100, 10, c, border=1)
        pdf.cell(45, 10, calc, border=1)
        pdf.cell(45, 10, tot, border=1, ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 245, 230)
    pdf.cell(0, 15, f"MARGEN NETO TOTAL: USD {neto_final:,.2f}", border=1, ln=True, align='C', fill=True)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# 2. SIDEBAR
with st.sidebar:
    st.header("📊 Parámetros")
    grano_sel = st.selectbox("Grano", list(precios_pizarra.keys()))
    toneladas = st.number_input("Toneladas", min_value=1.0, value=30.0)
    tarifa_ars = st.number_input("Tarifa Flete (ARS/TN)", value=28000.0)
    flete_usd_tn = tarifa_ars / dolar_bna
    
    st.divider()
    with st.expander("Ajustes de Gastos"):
        p_com = st.number_input("Comisión %", value=2.0)
        p_mer = st.number_input("Merma %", value=0.5)
        g_otros = st.number_input("Otros (Lab/Parit) USD/tn", value=1.5)

# 3. CUERPO Y MAPA
st.title("🚜 Optimizador AgroLogístico 2026")

m = folium.Map(location=[-33.5, -61.0], zoom_start=7)

# Iconos para Puertos (Rojo)
puertos = [
    {"nombre": "Puerto Rosario", "lat": -32.95, "lon": -60.64},
    {"nombre": "Puerto Bahía Blanca", "lat": -38.72, "lon": -62.27}
]
for p in puertos:
    folium.Marker([p['lat'], p['lon']], popup=p['nombre'], 
                  icon=folium.Icon(color="red", icon="ship", prefix="fa")).add_to(m)

# Iconos para Acopios (Verde)
for _, row in df_acopios.iterrows():
    folium.Marker([row['lat'], row['lon']], popup=f"Acopio: {row['nombre']}", 
                  icon=folium.Icon(color="green", icon="warehouse", prefix="fa")).add_to(m)

mapa_res = st_folium(m, width="100%", height=400)

# 4. LÓGICA COMPARATIVA
if mapa_res.get("last_clicked"):
    u_lat, u_lon = mapa_res["last_clicked"]["lat"], mapa_res["last_clicked"]["lng"]
    
    # Calcular todas las opciones
    opciones = []
    for p in puertos + df_acopios.to_dict('records'):
        dist = geodesic((u_lat, u_lon), (p['lat'], p['lon'])).km
        es_puerto = "Puerto" in p['nombre']
        precio_base = precios_pizarra[grano_sel] if es_puerto else precios_pizarra[grano_sel] - 8.0
        
        # Cálculo de Margen
        bruto = precio_base * toneladas
        desc_perc = bruto * ((p_com + p_mer) / 100)
        total_flete = flete_usd_tn * toneladas
        total_otros = g_otros * toneladas
        neto = bruto - desc_perc - total_flete - total_otros
        
        opciones.append({
            "Destino": p['nombre'],
            "Distancia (km)": round(dist, 1),
            "Precio Base USD": precio_base,
            "Margen Neto USD": round(neto, 2),
            # Guardamos info para el PDF
            "detalle": {
                "tn": toneladas, "precio_base": precio_base, "bruto": bruto,
                "perc_gasto": p_com + p_mer, "desc_perc": desc_perc,
                "flete_tn": round(flete_usd_tn, 2), "total_flete": total_flete,
                "otros_tn": g_otros, "total_otros": total_otros
            }
        })

    df_comp = pd.DataFrame(opciones)
    
    st.subheader("📋 Comparativa de Destinos en Tiempo Real")
    # Resaltar la mejor opción
    st.dataframe(
        df_comp.drop(columns="detalle").style.highlight_max(subset=["Margen Neto USD"], color="#d4edda"),
        use_container_width=True
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        seleccion = st.selectbox("Seleccionar destino para reporte PDF:", df_comp["Destino"])
        fila_sel = df_comp[df_comp["Destino"] == seleccion].iloc[0]
    
    with col2:
        pdf_bytes = generar_pdf_detalle(fila_sel['detalle'], seleccion, fila_sel['Margen Neto USD'])
        st.download_button(
            "📄 Descargar PDF con Desglose", 
            data=pdf_bytes, 
            file_name=f"Liquidacion_{seleccion}.pdf",
            mime="application/pdf"
        )
