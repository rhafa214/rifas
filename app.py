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

st.set_page_config(page_title="Gestor de Rifa Pro", layout="wide", page_icon="📊")

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
    ws.update_cell(2, 1, int(novo_total))
    ws.update_cell(2, 2, float(novo_preco))
    ws.update_cell(2, 3, str(novo_titulo))

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
            st.sidebar.error("Senha incorreta!")
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
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
st.title(f"🎟️ {dados['config']['titulo']}")

# --- CÁLCULOS PARA O DASHBOARD ---
total_numeros = int(dados["config"]["total_numeros"])
vendas = dados["vendas"]
total_vendidos = len(vendas)
faltam_vender = total_numeros - total_vendidos
porcentagem_vendas = (total_vendidos / total_numeros) * 100

pagos_count = sum(1 for v in vendas.values() if v["pago"])
preco_unit = float(dados["config"]["preco"])
arrecadado_pago = pagos_count * preco_unit
arrecadado_pendente = (total_vendidos - pagos_count) * preco_unit

# --- MÉTRICAS PRINCIPAIS ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{total_vendidos} ({porcentagem_vendas:.1f}%)")
c2.metric("Faltam Vender", faltam_vender)
c3.metric("Dinheiro em Caixa", f"R$ {arrecadado_pago:.2f}")
c4.metric("A Receber", f"R$ {arrecadado_pendente:.2f}")

st.divider()

# --- ABAS PRINCIPAIS ---
tab_mapa, tab_stats, tab_sorteio = st.tabs(["🗺️ Mapa de Números", "📊 Estatísticas Detalhadas", "🎲 Realizar Sorteio"])

with tab_mapa:
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Disponível")
    col_grade = st.columns(10)
    for i in range(1, total_numeros + 1):
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

with tab_stats:
    st.subheader("📈 Desempenho da Rifa")
    
    col_st1, col_st2 = st.columns(2)
    
    with col_st1:
        st.write("**Progresso de Vendas**")
        st.progress(porcentagem_vendas / 100)
        
        # Gráfico Simples de Vendas
        chart_data = pd.DataFrame({
            "Status": ["Vendidos", "Restantes"],
            "Quantidade": [total_vendidos, faltam_vender]
        })
        st.bar_chart(chart_data.set_index("Status"))

    with col_st2:
        st.write("**Resumo Financeiro**")
        finance_data = pd.DataFrame({
            "Financeiro": ["Em Caixa", "Pendente"],
            "Valor (R$)": [arrecadado_pago, arrecadado_pendente]
        })
        st.bar_chart(finance_data.set_index("Financeiro"), color="#28a745")

    st.divider()
    st.write("**Lista de Vendas Recentes**")
    if vendas:
        df_vendas = pd.DataFrame.from_dict(vendas, orient='index').reset_index()
        df_vendas.columns = ['Número', 'Nome', 'WhatsApp', 'Pago', 'Data']
        st.dataframe(df_vendas.sort_values(by="Número", key=lambda x: x.astype(int)), use_container_width=True)

with tab_sorteio:
    st.subheader("🎲 Sorteador")
    st.write("Apenas números **PAGOS (Verdes)** participam do sorteio.")
    if st.button("🚀 INICIAR SORTEIO AGORA", use_container_width=True):
        plista = [n for n, v in vendas.items() if v["pago"]]
        if plista:
            ph = st.empty()
            for i in range(3, 0, -1):
                ph.markdown(f"<h1 style='text-align:center; font-size:100px;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
            for _ in range(15):
                ph.markdown(f"<h1 style='text-align:center; font-size:100px;'>{random.randint(1, total_numeros):02d}</h1>", unsafe_allow_html=True); time.sleep(0.1)
            
            ganhador = random.choice(plista)
            st.balloons()
            ph.markdown(f"""
                <div style="text-align: center; background-color: #28a745; padding: 40px; border-radius: 20px; color: white;">
                    <h2 style="margin:0;">🏆 TEMOS UM GANHADOR!</h2>
                    <h1 style="font-size: 120px; margin:0;">{int(ganhador):02d}</h1>
                    <h3 style="margin:0;">👤 {vendas[ganhador]['nome']}</h3>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Não há nenhum número pago para sortear!")
