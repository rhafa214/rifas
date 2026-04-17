import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234" # Mude sua senha aqui
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Rifa Master Pro Cloud", layout="wide", page_icon="🎟️")

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
        # Carrega Vendas
        ws_vendas = sh.worksheet("vendas")
        # get_all_values evita erros de cabeçalho do get_all_records
        data = ws_vendas.get_all_values()
        
        vendas_dict = {}
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=[c.strip().lower() for c in data[0]])
            for _, row in df.iterrows():
                num = str(row['numero']).strip()
                if num:
                    vendas_dict[num] = {
                        "nome": row['nome'],
                        "tel": row['tel'],
                        "pago": str(row['pago']).upper() == 'TRUE',
                        "data": row['data']
                    }
        
        # Carrega Config
        ws_config = sh.worksheet("config")
        conf_data = ws_config.get_all_records()
        conf = conf_data[0] if conf_data else {"total_numeros": 100, "preco": 10.0}
        
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0}, "vendas": {}}

# --- FUNÇÕES DE EDIÇÃO NA PLANILHA ---
def salvar_venda(numero, nome, tel, pago):
    sh = conectar()
    ws = sh.worksheet("vendas")
    ws.append_row([str(numero), nome, tel, str(pago).upper(), datetime.now().strftime("%d/%m/%Y")])

def alterar_venda(numero, novo_nome, novo_pago):
    sh = conectar()
    ws = sh.worksheet("vendas")
    celula = ws.find(str(numero)) # Encontra a célula com o número
    if celula:
        ws.update_cell(celula.row, 2, novo_nome)      # Coluna B (nome)
        ws.update_cell(celula.row, 4, str(novo_pago).upper()) # Coluna D (pago)

def excluir_venda(numero):
    sh = conectar()
    ws = sh.worksheet("vendas")
    celula = ws.find(str(numero))
    if celula:
        ws.delete_rows(celula.row)

# --- SISTEMA ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

dados = st.session_state.dados

# --- BARRA LATERAL ---
st.sidebar.title("🔐 Administração")
if not st.session_state.autenticado:
    with st.sidebar:
        senha_in = st.text_input("Senha:", type="password")
        if st.button("Acessar Painel"):
            if senha_in == SENHA_MESTRE:
                st.session_state.autenticado = True
                st.rerun()
else:
    with st.sidebar:
        if st.button("🚪 Sair do Painel"):
            st.session_state.autenticado = False
            st.rerun()
        
        st.divider()
        abas = st.tabs(["📝 Vender", "✏️ Editar/Excluir", "⚙️ Ajustes"])
        
        with abas[0]: # VENDER
            livres = [n for n in range(1, dados["config"]["total_numeros"]+1) if str(n) not in dados["vendas"]]
            with st.form("venda_form", clear_on_submit=True):
                nums = st.multiselect("Números", livres)
                nome = st.text_input("Nome Comprador")
                pago = st.checkbox("Pago?")
                if st.form_submit_button("Registrar"):
                    if nums and nome:
                        for n in nums:
                            salvar_venda(n, nome, "", pago)
                        st.session_state.dados = carregar_dados()
                        st.rerun()

        with abas[1]: # EDITAR / EXCLUIR
            if dados["vendas"]:
                n_edit = st.selectbox("Escolha o número vendido:", sorted(dados["vendas"].keys(), key=int))
                info = dados["vendas"][n_edit]
                
                novo_n = st.text_input("Nome", value=info['nome'])
                novo_p = st.checkbox("Está pago?", value=info['pago'])
                
                col1, col2 = st.columns(2)
                if col1.button("✅ Salvar"):
                    alterar_venda(n_edit, novo_n, novo_p)
                    st.session_state.dados = carregar_dados()
                    st.rerun()
                if col2.button("🗑️ Excluir"):
                    excluir_venda(n_edit)
                    st.session_state.dados = carregar_dados()
                    st.rerun()

        with abas[2]: # AJUSTES
            if st.checkbox("Habilitar Reset"):
                if st.button("🔴 ZERAR TUDO"):
                    sh = conectar()
                    ws = sh.worksheet("vendas")
                    ws.clear()
                    ws.append_row(["numero", "nome", "tel", "pago", "data"])
                    st.session_state.dados = carregar_dados()
                    st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("🎟️ Rifa Master Cloud")

# Métricas
vendas = dados["vendas"]
pagos = sum(1 for v in vendas.values() if v["pago"])
arrecadado = pagos * dados["config"]["preco"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", len(vendas))
c2.metric("Pagos (Verde)", pagos)
c3.metric("Arrecadado", f"R$ {arrecadado:.2f}")
c4.metric("Pendentes", f"R$ {(len(vendas)-pagos)*dados['config']['preco']:.2f}")

st.divider()

# SORTEADOR
if st.button("🎲 REALIZAR SORTEIO", use_container_width=True):
    pagos_lista = [n for n, v in vendas.items() if v["pago"]]
    if pagos_lista:
        placeholder = st.empty()
        for i in range(3, 0, -1):
            placeholder.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True)
            time.sleep(1)
        ganhador = random.choice(pagos_lista)
        st.balloons()
        placeholder.markdown(f"""
            <div style="text-align: center; background-color: #28a745; padding: 20px; border-radius: 15px; color: white;">
                <h1>🏆 GANHADOR: {int(ganhador):02d}</h1>
                <h3>👤 {vendas[ganhador]['nome']}</h3>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Nenhum número pago para sortear.")

st.divider()

# MAPA VISUAL
st.subheader("📍 Mapa de Números")
st.write("🟡 Disponível | 🔴 Pendente | 🟢 Pago")

col_grade = st.columns(10)
for i in range(1, dados["config"]["total_numeros"] + 1):
    n_s = str(i)
    with col_grade[(i-1) % 10]:
        if n_s in vendas:
            v = vendas[n_s]
            cor_ic = "🟢" if v['pago'] else "🔴"
            with st.popover(f"{i:02d} {cor_ic}", use_container_width=True):
                st.write(f"**Dono:** {v['nome']}")
                st.write(f"**Status:** {'Pago' if v['pago'] else 'Pendente'}")
        else:
            with st.popover(f"{i:02d} 🟡", use_container_width=True):
                st.write("✨ Disponível")

st.divider()
st.caption("Dica: Se o site não atualizar sozinho após uma alteração, clique em 'Sair do Painel' e entre novamente.")
