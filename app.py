import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Gestor de Rifa Pro", layout="wide", page_icon="🎟️")

# --- CONEXÃO GOOGLE SHEETS ---
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_dict("suas-credenciais.json", scope)
    client = gspread.authorize(creds)
    return client.open(NOME_PLANILHA)

def carregar_dados():
    try:
        sh = conectar()
        # 1. Carrega Vendas
        ws_vendas = sh.worksheet("vendas")
        data = ws_vendas.get_all_values()
        vendas_dict = {}
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=[c.strip().lower() for c in data[0]])
            for _, row in df.iterrows():
                num = str(row['numero']).strip()
                if num:
                    vendas_dict[num] = {
                        "nome": row['nome'], "tel": row['tel'],
                        "pago": str(row['pago']).upper() == 'TRUE', "data": row['data']
                    }
        
        # 2. Carrega Configurações (Título, Total, Preço)
        ws_config = sh.worksheet("config")
        conf_list = ws_config.get_all_records()
        if conf_list:
            conf = conf_list[0]
            # Garante que o campo titulo existe no dicionário
            if "titulo" not in conf: conf["titulo"] = "Minha Rifa"
        else:
            conf = {"total_numeros": 100, "preco": 10.0, "titulo": "Minha Rifa"}
        
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa Master"}, "vendas": {}}

# --- FUNÇÕES DE ATUALIZAÇÃO ---
def atualizar_venda(numero, novo_nome, novo_pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, novo_nome)
        ws.update_cell(cel.row, 4, str(novo_pago).upper())

def excluir_venda(numero):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel: ws.delete_rows(cel.row)

def atualizar_configuracoes(novo_titulo, novo_total, novo_preco):
    sh = conectar(); ws = sh.worksheet("config")
    # Atualiza a linha 2 da aba config
    ws.update_cell(2, 1, novo_total)  # Coluna A: total_numeros
    ws.update_cell(2, 2, novo_preco)  # Coluna B: preco
    ws.update_cell(2, 3, novo_titulo) # Coluna C: titulo

# --- INICIALIZAÇÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

dados = st.session_state.dados

# --- BARRA LATERAL ---
st.sidebar.title("🔐 Administração")
if not st.session_state.autenticado:
    senha_in = st.sidebar.text_input("Senha:", type="password")
    if st.sidebar.button("Acessar Painel"):
        if senha_in == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    abas = st.sidebar.tabs(["📝 Vender", "✏️ Editar", "⚙️ Ajustes"])
    
    with abas[0]: # VENDER
        livres = [n for n in range(1, int(dados["config"]["total_numeros"])+1) if str(n) not in dados["vendas"]]
        with st.form("venda_form", clear_on_submit=True):
            nums = st.multiselect("Números", livres)
            nome_c = st.text_input("Nome")
            foi_pago = st.checkbox("Pago?")
            if st.form_submit_button("Registrar"):
                if nums and nome_c:
                    sh = conectar(); ws = sh.worksheet("vendas")
                    for n in nums:
                        ws.append_row([str(n), nome_c, "", str(foi_pago).upper(), datetime.now().strftime("%d/%m/%Y")])
                    st.session_state.dados = carregar_dados()
                    st.rerun()

    with abas[1]: # EDITAR
        if dados["vendas"]:
            n_edit = st.selectbox("Número vendido:", sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][n_edit]
            edit_nome = st.text_input("Nome", value=info['nome'])
            edit_pago = st.checkbox("Pago", value=info['pago'])
            c1, c2 = st.columns(2)
            if c1.button("Salvar"):
                atualizar_venda(n_edit, edit_nome, edit_pago)
                st.session_state.dados = carregar_dados()
                st.rerun()
            if c2.button("Excluir"):
                excluir_venda(n_edit)
                st.session_state.dados = carregar_dados()
                st.rerun()

    with abas[2]: # AJUSTES (AQUI MUDA O NOME DA RIFA)
        st.subheader("Configurações da Rifa")
        nome_rifa_input = st.text_input("Nome da Rifa", value=dados["config"]["titulo"])
        total_in = st.number_input("Total de Números", value=int(dados["config"]["total_numeros"]))
        preco_in = st.number_input("Preço por Número", value=float(dados["config"]["preco"]))
        
        if st.button("Atualizar Rifa"):
            atualizar_configuracoes(nome_rifa_input, total_in, preco_in)
            st.success("Configurações atualizadas!")
            st.session_state.dados = carregar_dados()
            st.rerun()
            
        st.divider()
        if st.checkbox("Liberar Reset"):
            if st.button("🔴 ZERAR TUDO"):
                sh = conectar(); ws = sh.worksheet("vendas"); ws.clear()
                ws.append_row(["numero", "nome", "tel", "pago", "data"])
                st.session_state.dados = carregar_dados()
                st.rerun()

# --- INTERFACE PRINCIPAL ---
# O TÍTULO AGORA VEM DA PLANILHA
st.title(f"🎟️ {dados['config']['titulo']}")

# Métricas
vendas = dados["vendas"]
pagos = sum(1 for v in vendas.values() if v["pago"])
arrecadado = pagos * float(dados["config"]["preco"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", len(vendas))
c2.metric("Pagos", pagos)
c3.metric("Arrecadado", f"R$ {arrecadado:.2f}")
c4.metric("Pendentes", f"R$ {(len(vendas)-pagos)*float(dados['config']['preco']):.2f}")

st.divider()

# SORTEADOR
if st.button("🎲 REALIZAR SORTEIO", use_container_width=True):
    plista = [n for n, v in vendas.items() if v["pago"]]
    if plista:
        ph = st.empty()
        for i in range(3, 0, -1):
            ph.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
        ganhador = random.choice(plista)
        st.balloons()
        ph.markdown(f"""<div style="text-align: center; background-color: #28a745; padding: 20px; border-radius: 15px; color: white;">
            <h1>🏆 GANHADOR: {int(ganhador):02d}</h1><h3>👤 {vendas[ganhador]['nome']}</h3></div>""", unsafe_allow_html=True)
    else: st.error("Sem números pagos.")

st.divider()

# MAPA
st.subheader("📍 Mapa de Números")
col_grade = st.columns(10)
for i in range(1, int(dados["config"]["total_numeros"]) + 1):
    n_s = str(i)
    with col_grade[(i-1) % 10]:
        if n_s in vendas:
            v = vendas[n_s]
            cor = "🟢" if v['pago'] else "🔴"
            with st.popover(f"{i:02d} {cor}", use_container_width=True):
                st.write(f"**Dono:** {v['nome']}")
        else:
            with st.popover(f"{i:02d} 🟡", use_container_width=True):
                st.write("✨ Disponível")
