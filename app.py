import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time
import urllib.parse

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
    .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
    .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
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
        if conf_list:
            conf = conf_list[0]
            for p in ["titulo", "premio1", "premio2", "premio3", "data_sorteio"]:
                if p not in conf: conf[p] = ""
        else:
            conf = {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa", "data_sorteio": "2024-12-31 20:00:00"}
        
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0, "titulo": "Erro"}, "vendas": {}}

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
st.sidebar.title("🔐 Painel do Dono")
if not st.session_state.autenticado:
    senha_in = st.sidebar.text_input("Senha Admin:", type="password")
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
            tel_c = st.text_input("WhatsApp (com DDD)")
            foi_pago = st.checkbox("Está Pago?")
            if st.form_submit_button("Confirmar Registro"):
                if nums and nome_c:
                    sh = conectar(); ws = sh.worksheet("vendas")
                    for n in nums:
                        ws.append_row([str(n), nome_c, tel_c, str(foi_pago).upper(), datetime.now().strftime("%d/%m/%Y")])
                    st.success("Registrado com sucesso!")
                    st.session_state.dados = carregar_dados()
                    st.rerun()

    with aba_s[1]:
        if dados["vendas"]:
            n_edit = st.selectbox("Número para alterar:", sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][n_edit]
            e_nome = st.text_input("Nome", value=info['nome'])
            e_tel = st.text_input("WhatsApp", value=info['tel'])
            e_pago = st.checkbox("Pago?", value=info['pago'])
            c1, c2 = st.columns(2)
            if c1.button("Salvar"):
                atualizar_venda(n_edit, e_nome, e_tel, e_pago)
                st.session_state.dados = carregar_dados()
                st.rerun()
            if c2.button("Excluir"):
                excluir_venda(n_edit)
                st.session_state.dados = carregar_dados()
                st.rerun()

    with aba_s[2]:
        n_tit = st.text_input("Nome da Rifa", value=dados["config"]["titulo"])
        n_tot = st.number_input("Qtd Números", value=int(dados["config"]["total_numeros"]))
        n_pre = st.number_input("Preço R$", value=float(dados["config"]["preco"]))
        st.write("Data:")
        d_sort = st.text_input("YYYY-MM-DD HH:MM:SS", value=dados["config"]["data_sorteio"])
        st.write("Prêmios:")
        p1 = st.text_input("1º", value=dados["config"].get("premio1"))
        p2 = st.text_input("2º", value=dados["config"].get("premio2"))
        p3 = st.text_input("3º", value=dados["config"].get("premio3"))
        if st.button("Atualizar Tudo"):
            atualizar_configuracoes(n_tit, n_tot, n_pre, p1, p2, p3, d_sort)
            st.session_state.dados = carregar_dados(); st.rerun()

# --- INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🎟️ {dados['config']['titulo']}</h1>", unsafe_allow_html=True)

# Cronômetro
try:
    alvo = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    dif = alvo - datetime.now()
    if dif.total_seconds() > 0:
        st.markdown(f"<div class='countdown-box'>⏳ Faltam {dif.days} dias e {dif.seconds//3600} horas para o grande sorteio!</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='countdown-box' style='color:red;'>🏁 Vendas Encerradas - Prepare-se para o Sorteio!</div>", unsafe_allow_html=True)
except: pass

# Métricas
total_n = int(dados["config"]["total_numeros"])
vendas = dados["vendas"]
v_count = len(vendas)
p_count = sum(1 for v in vendas.values() if v["pago"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{v_count} ({(v_count/total_n)*100:.1f}%)")
c2.metric("Disponíveis", total_n - v_count)
c3.metric("Confirmado", f"R$ {p_count * float(dados['config']['preco']):.2f}")
c4.metric("Pendentes", f"R$ {(v_count - p_count) * float(dados['config']['preco']):.2f}")

st.divider()

# Busca para Clientes
st.subheader("🔍 Localizar meus Números")
busca_cliente = st.text_input("Digite seu nome para ver seus números:", placeholder="Ex: Danilo")
if busca_cliente:
    meus_nums = [n for n, v in vendas.items() if busca_cliente.lower() in v['nome'].lower()]
    if meus_nums:
        st.success(f"Olá {busca_cliente}, seus números são: **{', '.join(sorted(meus_nums, key=int))}**")
    else:
        st.warning("Nenhum número encontrado para este nome.")

# ABAS
t_mapa, t_sorteio, t_stats = st.tabs(["🗺️ Mapa de Números", "🎲 Sorteador", "📊 Relatórios"])

with t_mapa:
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Livre")
    num_cols = 5 if v_count > 0 else 10 # Mobile friendly
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
                            # Link WhatsApp (Apenas visível para admin se quiser)
                            if st.session_state.autenticado and v['tel']:
                                msg = urllib.parse.quote(f"Olá {v['nome']}, estou confirmando seu número {n} na {dados['config']['titulo']}!")
                                st.markdown(f"[💬 Chamar no Whats](https://wa.me/55{v['tel']}?text={msg})")
                    else:
                        with st.popover(f"{n:02d} 🟡", use_container_width=True):
                            st.write("✨ Disponível")

with t_sorteio:
    st.subheader("🎲 Sorteio Oficial")
    if st.button("🗑️ Limpar Testes"): st.session_state.vencedores = {}; st.rerun()
    
    def animar(pagos):
        ph = st.empty()
        for i in range(3,0,-1): ph.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
        res = random.choice(pagos); st.balloons(); return res

    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p3:
        st.write(f"3º: {dados['config'].get('premio3')}")
        if st.button("Sortear 3º"):
            if pagos_l: 
                r = animar(pagos_l)
                st.session_state.vencedores["3"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "3" in st.session_state.vencedores: 
            st.success(f"🥉 {st.session_state.vencedores['3']['n']} - {st.session_state.vencedores['3']['nome']}")

    with col_p2:
        st.write(f"2º: {dados['config'].get('premio2')}")
        if st.button("Sortear 2º"):
            lf = [n for n in pagos_l if n != st.session_state.vencedores.get("3",{}).get("n")]
            if lf: 
                r = animar(lf)
                st.session_state.vencedores["2"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "2" in st.session_state.vencedores: 
            st.success(f"🥈 {st.session_state.vencedores['2']['n']} - {st.session_state.vencedores['2']['nome']}")

    with col_p1:
        st.write(f"1º: {dados['config'].get('premio1')}")
        if st.button("Sortear 1º"):
            lf = [n for n in pagos_l if n not in [st.session_state.vencedores.get(x,{}).get("n") for x in ["2","3"]]]
            if lf: 
                r = animar(lf)
                st.session_state.vencedores["1"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "1" in st.session_state.vencedores: 
            st.success(f"🥇 {st.session_state.vencedores['1']['n']} - {st.session_state.vencedores['1']['nome']}")

with t_stats:
    st.subheader("📊 Relatório Detalhado")
    if vendas:
        df = pd.DataFrame.from_dict(vendas, orient='index').reset_index()
        df.columns = ['Nº', 'Nome', 'Zap', 'Pago', 'Data']
        st.dataframe(df.sort_values(by="Nº", key=lambda x: x.astype(int)), use_container_width=True)
    st.divider()
    st.write("**Regras:** O sorteio será realizado na data acima. Números não pagos até 24h antes serão liberados.")
