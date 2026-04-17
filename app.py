import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
import time

# --- CONFIGURAÇÕES ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Gestor de Rifa Master", layout="wide", page_icon="📅")

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
            # Garantir campos novos incluindo data_sorteio
            defaults = {"titulo": "Rifa", "premio1": "", "premio2": "", "premio3": "", "data_sorteio": "2024-12-31 20:00:00"}
            for k, v in defaults.items():
                if k not in conf: conf[k] = v
        else:
            conf = {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa", "data_sorteio": "2024-12-31 20:00:00"}
        
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return {"config": {"total_numeros": 100, "preco": 10.0, "titulo": "Erro", "data_sorteio": "2024-12-31 20:00:00"}, "vendas": {}}

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

def atualizar_configuracoes(novo_titulo, novo_total, novo_preco, p1, p2, p3, nova_data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(novo_total))
    ws.update_cell(2, 2, float(novo_preco))
    ws.update_cell(2, 3, str(novo_titulo))
    ws.update_cell(2, 4, str(p1))
    ws.update_cell(2, 5, str(p2))
    ws.update_cell(2, 6, str(p3))
    ws.update_cell(2, 7, str(nova_data))

# --- INICIALIZAÇÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'dados' not in st.session_state: st.session_state.dados = carregar_dados()
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}

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
    
    abas_side = st.sidebar.tabs(["📝 Vender", "✏️ Editar", "⚙️ Ajustes"])
    
    with abas_side[0]:
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

    with abas_side[1]:
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

    with abas_side[2]:
        st.subheader("Configurações")
        nome_rifa_input = st.text_input("Nome da Rifa", value=dados["config"]["titulo"])
        total_in = st.number_input("Total de Números", value=int(dados["config"]["total_numeros"]))
        preco_in = st.number_input("Preço por Número", value=float(dados["config"]["preco"]))
        
        # --- EDIÇÃO DA DATA DO SORTEIO ---
        st.write("**Data do Sorteio:**")
        try:
            data_atual_config = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
        except:
            data_atual_config = datetime.now()
            
        nova_data_sorteio = st.date_input("Dia", data_atual_config.date())
        nova_hora_sorteio = st.time_input("Hora", data_atual_config.time())
        data_final_str = f"{nova_data_sorteio} {nova_hora_sorteio}"
        
        st.write("**Prêmios:**")
        p1 = st.text_input("1º Prêmio", value=dados["config"].get("premio1", ""))
        p2 = st.text_input("2º Prêmio", value=dados["config"].get("premio2", ""))
        p3 = st.text_input("3º Prêmio", value=dados["config"].get("premio3", ""))
        
        if st.button("Atualizar Tudo"):
            atualizar_configuracoes(nome_rifa_input, total_in, preco_in, p1, p2, p3, data_final_str)
            st.success("Configurações atualizadas!")
            st.session_state.dados = carregar_dados()
            st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title(f"🎟️ {dados['config']['titulo']}")

# --- LÓGICA DO CRONÔMETRO ---
try:
    data_alvo = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    agora = datetime.now()
    diferenca = data_alvo - agora

    if diferenca.total_seconds() > 0:
        dias = diferenca.days
        horas, rem = divmod(diferenca.seconds, 3600)
        minutos, segundos = divmod(rem, 60)
        st.info(f"⏳ **O sorteio será em:** {dias} dias, {horas}h {minutos}min")
    else:
        st.error("🏁 **O período de vendas encerrou! Prepare-se para o sorteio.**")
except:
    st.warning("⚠️ Data do sorteio não configurada corretamente.")

# Métricas
total_n = int(dados["config"]["total_numeros"])
vendas = dados["vendas"]
vendidos = len(vendas)
pagos_c = sum(1 for v in vendas.values() if v["pago"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Vendidos", f"{vendidos} ({ (vendidos/total_n)*100 :.1f}%)")
m2.metric("Faltam Vender", total_n - vendidos)
m3.metric("Confirmado", f"R$ {pagos_c * float(dados['config']['preco']):.2f}")
m4.metric("Pendentes", f"R$ {(vendidos - pagos_c) * float(dados['config']['preco']):.2f}")

st.divider()

# ABAS (Mapa, Sorteador, Estatísticas)
tab_mapa, tab_sorteio, tab_stats = st.tabs(["🗺️ Mapa", "🎲 Sorteador", "📊 Estatísticas"])

# ... (Restante do código das abas Mapa, Sorteador e Stats permanece igual ao anterior)
with tab_mapa:
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Disponível")
    col_g = st.columns(10)
    for i in range(1, total_n + 1):
        ns = str(i)
        with col_g[(i-1) % 10]:
            if ns in vendas:
                v = vendas[ns]
                cor = "🟢" if v['pago'] else "🔴"
                with st.popover(f"{i:02d} {cor}", use_container_width=True):
                    st.write(f"**Dono:** {v['nome']}")
            else:
                with st.popover(f"{i:02d} 🟡", use_container_width=True):
                    st.write("✨ Disponível")

with tab_sorteio:
    st.subheader("🎲 Realizar Sorteio")
    if st.button("🗑️ Limpar Ganhadores"):
        st.session_state.vencedores = {}; st.rerun()
    
    st.divider()
    col_p1, col_p2, col_p3 = st.columns(3)
    
    def animar_sorteio(lista_pagos):
        ph = st.empty()
        for i in range(3, 0, -1):
            ph.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
        res = random.choice(lista_pagos)
        st.balloons()
        return res

    pagos_lista = [n for n, v in vendas.items() if v["pago"]]

    with col_p3:
        st.write(f"**3º Prêmio:** {dados['config'].get('premio3')}")
        if st.button("Sortear 3º"):
            if pagos_lista:
                r = animar_sorteio(pagos_lista)
                st.session_state.vencedores["3"] = {"num": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "3" in st.session_state.vencedores:
            v = st.session_state.vencedores["3"]
            st.success(f"🥉 {v['num']} - {v['nome']}")

    with col_p2:
        st.write(f"**2º Prêmio:** {dados['config'].get('premio2')}")
        if st.button("Sortear 2º"):
            l_f = [n for n in pagos_lista if n != st.session_state.vencedores.get("3", {}).get("num")]
            if l_f:
                r = animar_sorteio(l_f)
                st.session_state.vencedores["2"] = {"num": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "2" in st.session_state.vencedores:
            v = st.session_state.vencedores["2"]
            st.success(f"🥈 {v['num']} - {v['nome']}")

    with col_p1:
        st.write(f"**1º Prêmio:** {dados['config'].get('premio1')}")
        if st.button("Sortear 1º"):
            l_f = [n for n in pagos_lista if n not in [st.session_state.vencedores.get(x,{}).get("num") for x in ["2","3"]]]
            if l_f:
                r = animar_sorteio(l_f)
                st.session_state.vencedores["1"] = {"num": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "1" in st.session_state.vencedores:
            v = st.session_state.vencedores["1"]
            st.success(f"🥇 {v['num']} - {v['nome']}")

with tab_stats:
    st.subheader("📊 Estatísticas")
    st.progress(vendidos/total_n)
    if vendas:
        df_v = pd.DataFrame.from_dict(vendas, orient='index').reset_index()
        df_v.columns = ['Número', 'Nome', 'WhatsApp', 'Pago', 'Data']
        st.dataframe(df_v.sort_values(by="Número", key=lambda x: x.astype(int)), use_container_width=True)
