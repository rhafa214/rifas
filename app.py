import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234"

st.set_page_config(page_title="Rifa Master Pro Cloud", layout="wide", page_icon="🎟️")

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Tenta ler dos Secrets do Streamlit Cloud
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        # Se falhar (local), tenta ler do arquivo JSON
        creds = ServiceAccountCredentials.from_json_keyfile_dict("seu-arquivo-local.json", scope)
    
    client = gspread.authorize(creds)
    return client.open("DB_Rifa")

def carregar_dados():
    try:
        sh = conectar_google_sheets()
        
        # 1. Carrega Vendas de forma segura
        ws_vendas = sh.worksheet("vendas")
        lista_vendas = ws_vendas.get_all_records() # Tenta ler como dicionário
        
        vendas_dict = {}
        if lista_vendas:
            for item in lista_vendas:
                # Usa .get() para evitar o KeyError caso a coluna não exista
                num = str(item.get('numero', ''))
                if num:
                    vendas_dict[num] = {
                        "nome": item.get('nome', 'Sem Nome'),
                        "tel": str(item.get('tel', '')),
                        "pago": str(item.get('pago', '')).upper() == 'TRUE',
                        "data": item.get('data', '')
                    }
        
        # 2. Carrega Configurações
        ws_config = sh.worksheet("config")
        lista_config = ws_config.get_all_records()
        
        if lista_config:
            conf = lista_config[0]
        else:
            conf = {"total_numeros": 100, "preco": 10.0}
            
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0}, "vendas": {}}

def registrar_venda_google(numero, nome, tel, pago):
    try:
        sh = conectar_google_sheets()
        ws = sh.worksheet("vendas")
        ws.append_row([numero, nome, tel, str(pago).upper(), datetime.now().strftime("%d/%m/%Y")])
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- CONTROLE DE ACESSO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Carregamento dos dados
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

dados = st.session_state.dados

# --- BARRA LATERAL ---
st.sidebar.title("🔐 Administração")
if not st.session_state.autenticado:
    senha_input = st.sidebar.text_input("Senha:", type="password")
    if st.sidebar.button("Acessar"):
        if senha_input == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Incorreta")
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    aba_admin = st.sidebar.tabs(["📝 Vender", "⚙️ Ajustes"])
    
    with aba_admin[0]:
        livres = [n for n in range(1, dados["config"]["total_numeros"]+1) if str(n) not in dados["vendas"]]
        with st.form("form_venda", clear_on_submit=True):
            selecionados = st.multiselect("Números", livres)
            nome_comp = st.text_input("Nome do Comprador")
            is_pago = st.checkbox("Está pago?")
            if st.form_submit_button("Confirmar Venda"):
                if selecionados and nome_comp:
                    for n in selecionados:
                        registrar_venda_google(n, nome_comp, "", is_pago)
                    st.success("Registrado!")
                    st.session_state.dados = carregar_dados()
                    st.rerun()

    with aba_admin[1]:
        if st.checkbox("Habilitar Reiniciar"):
            if st.button("🔴 ZERAR TODA A RIFA"):
                sh = conectar_google_sheets()
                ws = sh.worksheet("vendas")
                ws.clear()
                ws.append_row(["numero", "nome", "tel", "pago", "data"])
                st.session_state.dados = carregar_dados()
                st.rerun()

# --- PAINEL PRINCIPAL ---
st.title("🎟️ Gestão de Rifa Master")

# Métricas
vendas = dados["vendas"]
total_vendas = len(vendas)
pagos = sum(1 for v in vendas.values() if v["pago"])
arrecadado = pagos * dados["config"]["preco"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", total_vendas)
c2.metric("Pagos (Verde)", pagos)
c3.metric("Arrecadado", f"R$ {arrecadado:.2f}")
c4.metric("Pendentes", f"R$ {(total_vendas-pagos)*dados['config']['preco']:.2f}")

st.divider()

# SORTEADOR
if st.button("🎲 REALIZAR SORTEIO", use_container_width=True):
    apenas_pagos = [n for n, v in vendas.items() if v["pago"]]
    if apenas_pagos:
        placeholder = st.empty()
        for i in range(3, 0, -1):
            placeholder.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True)
            time.sleep(1)
        vencedor = random.choice(apenas_pagos)
        st.balloons()
        placeholder.markdown(f"""
            <div style="text-align: center; background-color: #28a745; padding: 20px; border-radius: 15px; color: white;">
                <h1>🏆 VENCEDOR: {int(vencedor):02d}</h1>
                <h3>👤 {vendas[vencedor]['nome']}</h3>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Ninguém pagou ainda!")

st.divider()

# MAPA VISUAL COM CORES SOLICITADAS
st.subheader("📍 Mapa de Números (Clique para detalhes)")
st.write("🟡 Disponível | 🔴 Sem Pagar | 🟢 Pago")

col_grade = st.columns(10)
for i in range(1, dados["config"]["total_numeros"] + 1):
    n_str = str(i)
    with col_grade[(i-1) % 10]:
        if n_str in vendas:
            info = vendas[n_str]
            # VERDE se pago, VERMELHO se pendente
            cor_icon = "🟢" if info['pago'] else "🔴"
            with st.popover(f"{i:02d} {cor_icon}", use_container_width=True):
                st.write(f"**Dono:** {info['nome']}")
                st.write(f"**Status:** {'Pago' if info['pago'] else 'Pendente'}")
        else:
            # AMARELO se disponível
            with st.popover(f"{i:02d} 🟡", use_container_width=True):
                st.write("✨ Disponível")
