import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time
import urllib.parse
import re

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- ESTILO CSS PERSONALIZADO (BOTÃO WHATSAPP INCLUÍDO) ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
    .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
    .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
    
    /* Botão WhatsApp Estilizado */
    .btn-whatsapp {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 12px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        width: 100%;
        gap: 10px;
        transition: 0.3s;
        border: none;
        margin-top: 10px;
    }
    .btn-whatsapp:hover {
        background-color: #128C7E;
        text-decoration: none;
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)

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
        ws_config = sh.worksheet("config")
        conf_list = ws_config.get_all_records()
        conf = conf_list[0] if conf_list else {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa"}
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0, "titulo": "Erro"}, "vendas": {}}

# --- FUNÇÕES DE ATUALIZAÇÃO ---
def atualizar_venda(numero, novo_nome, novo_tel, novo_pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, novo_nome)
        ws.update_cell(cel.row, 3, novo_tel)
        ws.update_cell(cel.row, 4, str(novo_pago).upper())

def excluir_venda(numero):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel: ws.delete_rows(cel.row)

def atualizar_configuracoes(novo_titulo, novo_total, novo_preco, p1, p2, p3, nova_data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(novo_total)); ws.update_cell(2, 2, float(novo_preco))
    ws.update_cell(2, 3, str(novo_titulo)); ws.update_cell(2, 4, str(p1))
    ws.update_cell(2, 5, str(p2)); ws.update_cell(2, 6, str(p3))
    ws.update_cell(2, 7, str(nova_data))

# --- INICIALIZAÇÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'dados' not in st.session_state: st.session_state.dados = carregar_dados()
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}

dados = st.session_state.dados

# --- BARRA LATERAL ---
st.sidebar.title("🔐 Painel Administrativo")
if not st.session_state.autenticado:
    senha_in = st.sidebar.text_input("Senha:", type="password")
    if st.sidebar.button("Acessar"):
        if senha_in == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    st.sidebar.divider()
    aba_s = st.sidebar.tabs(["📝 Venda", "✏️ Editar", "⚙️ Config"])
    
    with aba_s[0]:
        livres = [n for n in range(1, int(dados["config"]["total_numeros"])+1) if str(n) not in dados["vendas"]]
        with st.form("venda_form", clear_on_submit=True):
            nums = st.multiselect("Números", livres)
            nome_c = st.text_input("Nome")
            tel_c = st.text_input("WhatsApp (Ex: 11999998888)")
            foi_pago = st.checkbox("Já Pago?")
            if st.form_submit_button("Confirmar Registro"):
                if nums and nome_c:
                    sh = conectar(); ws = sh.worksheet("vendas")
                    for n in nums:
                        ws.append_row([str(n), nome_c, tel_c, str(foi_pago).upper(), datetime.now().strftime("%d/%m/%Y")])
                    st.session_state.dados = carregar_dados(); st.rerun()

    with aba_s[1]:
        if dados["vendas"]:
            n_edit = st.selectbox("Nº para alterar:", sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][n_edit]
            e_nome = st.text_input("Nome", value=info['nome'])
            e_tel = st.text_input("WhatsApp", value=info['tel'])
            e_pago = st.checkbox("Pago?", value=info['pago'])
            c1, c2 = st.columns(2)
            if c1.button("Salvar"):
                atualizar_venda(n_edit, e_nome, e_tel, e_pago)
                st.session_state.dados = carregar_dados(); st.rerun()
            if c2.button("Excluir"):
                excluir_venda(n_edit)
                st.session_state.dados = carregar_dados(); st.rerun()

    with aba_s[2]:
        n_tit = st.text_input("Título", value=dados["config"]["titulo"])
        n_tot = st.number_input("Total Números", value=int(dados["config"]["total_numeros"]))
        n_pre = st.number_input("Preço R$", value=float(dados["config"]["preco"]))
        d_sort = st.text_input("Data Sorteio", value=dados["config"].get("data_sorteio", "2024-12-31 20:00:00"))
        p1 = st.text_input("1º Prêmio", value=dados["config"].get("premio1"))
        p2 = st.text_input("2º Prêmio", value=dados["config"].get("premio2"))
        p3 = st.text_input("3º Prêmio", value=dados["config"].get("premio3"))
        if st.button("Atualizar Configurações"):
            atualizar_configuracoes(n_tit, n_tot, n_pre, p1, p2, p3, d_sort)
            st.session_state.dados = carregar_dados(); st.rerun()

# --- INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🎟️ {dados['config']['titulo']}</h1>", unsafe_allow_html=True)

# Cronômetro Simples
try:
    alvo = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    dif = alvo - datetime.now()
    if dif.total_seconds() > 0:
        st.markdown(f"<div class='countdown-box'>⏳ Sorteio em {dif.days} dias e {dif.seconds//3600}h</div>", unsafe_allow_html=True)
except: pass

# Métricas
total_n = int(dados["config"]["total_numeros"])
vendas = dados["vendas"]
v_count = len(vendas)
p_count = sum(1 for v in vendas.values() if v["pago"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Vendidos", f"{v_count}")
m2.metric("Disponíveis", total_n - v_count)
m3.metric("Confirmado", f"R$ {p_count * float(dados['config']['preco']):.2f}")
m4.metric("Pendentes", f"R$ {(v_count - p_count) * float(dados['config']['preco']):.2f}")

st.divider()

# Busca Cliente
busca = st.text_input("🔍 Ver meus números (digite seu nome):")
if busca:
    encontrados = [n for n, v in vendas.items() if busca.lower() in v['nome'].lower()]
    if encontrados: st.success(f"Seus números: {', '.join(sorted(encontrados, key=int))}")

# ABAS
t_mapa, t_sorteio, t_stats = st.tabs(["🗺️ Mapa", "🎲 Sorteador", "📊 Relatórios"])

with t_mapa:
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Disponível")
    num_cols = 5
    for i in range(0, total_n, num_cols):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            n = i + j + 1
            if n <= total_n:
                ns = str(n)
                with cols[j]:
                    if ns in vendas:
                        v = vendas[ns]
                        cor = "🟢" if v['pago'] else "🔴"
                        with st.popover(f"{n:02d} {cor}", use_container_width=True):
                            st.write(f"**Dono:** {v['nome']}")
                            st.write(f"**Status:** {'Pago' if v['pago'] else 'Pendente'}")
                            
                            # BOTÃO WHATSAPP VISUAL (Apenas Admin)
                            if st.session_state.autenticado and v['tel']:
                                # Limpa o número (remove tudo que não for dígito)
                                tel_limpo = re.sub(r'\D', '', v['tel'])
                                msg = urllib.parse.quote(f"Olá {v['nome']}, tudo bem? Estou confirmando seu número {n} na {dados['config']['titulo']}!")
                                # HTML do Botão
                                st.markdown(f"""
                                    <a href="https://wa.me/55{tel_limpo}?text={msg}" target="_blank" class="btn-whatsapp">
                                        <i class="fab fa-whatsapp" style="font-size:20px;"></i> Enviar Mensagem
                                    </a>
                                """, unsafe_allow_html=True)
                    else:
                        with st.popover(f"{n:02d} 🟡", use_container_width=True):
                            st.write("✨ Disponível")

with t_sorteio:
    st.subheader("🎲 Sorteio Oficial")
    if st.button("🗑️ Limpar Testes"): st.session_state.vencedores = {}; st.rerun()
    
    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    col_p1, col_p2, col_p3 = st.columns(3)
    
    def realizar_sorteio(lista):
        ph = st.empty()
        for i in range(3,0,-1): ph.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
        res = random.choice(lista); st.balloons(); return res

    with col_p3:
        st.write(f"3º: {dados['config'].get('premio3')}")
        if st.button("Sortear 3º"):
            if pagos_l: 
                r = realizar_sorteio(pagos_l)
                st.session_state.vencedores["3"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "3" in st.session_state.vencedores: st.success(f"🥉 {st.session_state.vencedores['3']['n']} - {st.session_state.vencedores['3']['nome']}")

    with col_p2:
        st.write(f"2º: {dados['config'].get('premio2')}")
        if st.button("Sortear 2º"):
            lf = [n for n in pagos_l if n != st.session_state.vencedores.get("3",{}).get("n")]
            if lf: 
                r = realizar_sorteio(lf)
                st.session_state.vencedores["2"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "2" in st.session_state.vencedores: st.success(f"🥈 {st.session_state.vencedores['2']['n']} - {st.session_state.vencedores['2']['nome']}")

    with col_p1:
        st.write(f"1º: {dados['config'].get('premio1')}")
        if st.button("Sortear 1º"):
            lf = [n for n in pagos_l if n not in [st.session_state.vencedores.get(x,{}).get("n") for x in ["2","3"]]]
            if lf: 
                r = realizar_sorteio(lf)
                st.session_state.vencedores["1"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "1" in st.session_state.vencedores: st.success(f"🥇 {st.session_state.vencedores['1']['n']} - {st.session_state.vencedores['1']['nome']}")

with t_stats:
    if vendas:
        df = pd.DataFrame.from_dict(vendas, orient='index').reset_index()
        df.columns = ['Nº', 'Nome', 'Zap', 'Pago', 'Data']
        st.dataframe(df.sort_values(by="Nº", key=lambda x: x.astype(int)), use_container_width=True)
