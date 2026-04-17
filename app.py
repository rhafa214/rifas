import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time

# --- CONFIGURAÇÕES DE ACESSO ---
SENHA_MESTRE = "1234"

# Função para conectar ao Google Sheets
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # No Streamlit Cloud, usaremos st.secrets. No VS Code local, você usará o arquivo JSON.
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        # Se você estiver rodando local, ele procura o arquivo que você baixou
        creds = ServiceAccountCredentials.from_json_keyfile_dict("suas-credenciais.json", scope)
    
    client = gspread.authorize(creds)
    return client.open("DB_Rifa")

# Carregamento de Dados da Planilha
def carregar_dados():
    sh = conectar_google_sheets()
    
    # Carrega Vendas
    ws_vendas = sh.worksheet("vendas")
    df_vendas = pd.DataFrame(ws_vendas.get_all_records())
    vendas_dict = {}
    for _, row in df_vendas.iterrows():
        vendas_dict[str(row['numero'])] = {
            "nome": row['nome'], "tel": str(row['tel']), 
            "pago": True if str(row['pago']).upper() == 'TRUE' else False, 
            "data": row['data']
        }
    
    # Carrega Config
    ws_config = sh.worksheet("config")
    conf = ws_config.get_all_records()[0]
    
    return {"config": conf, "vendas": vendas_dict}

# Salvar Venda na Planilha
def registrar_venda_google(numero, nome, tel, pago):
    sh = conectar_google_sheets()
    ws = sh.worksheet("vendas")
    ws.append_row([numero, nome, tel, str(pago).upper(), datetime.now().strftime("%d/%m/%Y")])

# Zerar Planilha
def resetar_planilha_google():
    sh = conectar_google_sheets()
    ws = sh.worksheet("vendas")
    ws.clear()
    ws.append_row(["numero", "nome", "tel", "pago", "data"])

# --- INÍCIO DO APP ---
st.set_page_config(page_title="Rifa Profissional Cloud", layout="wide")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Carregamento inicial (usando cache para não ficar lento)
if 'dados' not in st.session_state or st.sidebar.button("🔄 Sincronizar Planilha"):
    with st.spinner("Conectando ao Google Sheets..."):
        st.session_state.dados = carregar_dados()

dados = st.session_state.dados

# --- BARRA LATERAL (ADMIN) ---
st.sidebar.title("🔐 Administração")
if not st.session_state.autenticado:
    senha_input = st.sidebar.text_input("Senha:", type="password")
    if st.sidebar.button("Entrar"):
        if senha_input == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
else:
    if st.sidebar.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()
    
    aba_admin = st.sidebar.tabs(["📝 Vender", "⚙️ Ajustes"])
    
    with aba_admin[0]: # VENDER
        livres = [n for n in range(1, dados["config"]["total_numeros"]+1) if str(n) not in dados["vendas"]]
        with st.form("venda"):
            seletor = st.multiselect("Números", livres)
            nome = st.text_input("Nome")
            pago = st.checkbox("Pago?")
            if st.form_submit_button("Confirmar"):
                for n in seletor:
                    registrar_venda_google(n, nome, "", pago)
                st.success("Salvo no Google Sheets!")
                st.session_state.dados = carregar_dados() # Atualiza
                st.rerun()

    with aba_admin[1]: # RESET
        if st.checkbox("Liberar Reset"):
            if st.button("🔴 ZERAR PLANILHA"):
                resetar_planilha_google()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("🎟️ Rifa Online (Google Sheets)")

# Métricas
vendas = dados["vendas"]
c1, c2, c3 = st.columns(3)
c1.metric("Vendidos", len(vendas))
c2.metric("Total de Números", dados["config"]["total_numeros"])
c3.metric("Arrecadado", f"R$ {sum(1 for v in vendas.values() if v['pago']) * dados['config']['preco']:.2f}")

# Mapa de Números
st.divider()
cols = st.columns(10)
for i in range(1, dados["config"]["total_numeros"] + 1):
    n_str = str(i)
    with cols[(i-1)%10]:
        if n_str in vendas:
            cor = "🟢" if vendas[n_str]["pago"] else "🔴"
            with st.popover(f"{i:02d} {cor}", use_container_width=True):
                st.write(f"Dono: {vendas[n_str]['nome']}")
        else:
            st.button(f"{i:02d} 🟡", key=f"btn_{i}", use_container_width=True, disabled=True)