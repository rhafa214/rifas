import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time
import urllib.parse
import re

# --- CONFIGURAÇÕES DE ACESSO ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- ESTILO CSS (VISUAL PROFISSIONAL) ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
    .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
    .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; }
    
    /* Botões WhatsApp */
    .btn-whatsapp { display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; transition: 0.3s; margin-top: 10px; }
    .btn-whatsapp:hover { background-color: #128C7E; transform: scale(1.02); text-decoration: none; }
    
    /* Botão Compartilhar Grupo */
    .btn-share { display: inline-flex; align-items: center; justify-content: center; background-color: #007bff; color: white !important; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; }
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
        # 1. Carrega Vendas (Robusto)
        ws_v = sh.worksheet("vendas")
        data_v = ws_v.get_all_values()
        vendas_dict = {}
        if len(data_v) > 1:
            df = pd.DataFrame(data_v[1:], columns=[c.strip().lower() for c in data_v[0]])
            for _, row in df.iterrows():
                num = str(row['numero']).strip()
                if num:
                    vendas_dict[num] = {
                        "nome": row.get('nome', 'Sem Nome'),
                        "tel": str(row.get('tel', '')),
                        "pago": str(row.get('pago', '')).upper() == 'TRUE',
                        "data": row.get('data', '')
                    }
        # 2. Carrega Config
        ws_c = sh.worksheet("config")
        conf_list = ws_c.get_all_records()
        if conf_list:
            conf = conf_list[0]
            # Fallbacks para colunas novas
            for k in ["titulo", "premio1", "premio2", "premio3", "data_sorteio"]:
                if k not in conf: conf[k] = ""
        else:
            conf = {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa Master", "data_sorteio": "2024-12-31 20:00:00"}
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# --- FUNÇÕES DE EDIÇÃO ---
def atualizar_venda_sheet(numero, nome, tel, pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, nome)
        ws.update_cell(cel.row, 3, tel)
        ws.update_cell(cel.row, 4, str(pago).upper())

def excluir_venda_sheet(numero):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel: ws.delete_rows(cel.row)

def salvar_config_sheet(titulo, total, preco, p1, p2, p3, data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(total)); ws.update_cell(2, 2, float(preco))
    ws.update_cell(2, 3, str(titulo)); ws.update_cell(2, 4, str(p1))
    ws.update_cell(2, 5, str(p2)); ws.update_cell(2, 6, str(p3))
    ws.update_cell(2, 7, str(data))

# --- INICIALIZAÇÃO DE ESTADO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}

dados = carregar_dados()
if not dados: st.stop()

# --- BARRA LATERAL (PAINEL ADMIN) ---
st.sidebar.title("🔐 Painel Administrativo")
if not st.session_state.autenticado:
    senha_in = st.sidebar.text_input("Senha Admin:", type="password")
    if st.sidebar.button("Entrar"):
        if senha_in == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
        else: st.sidebar.error("Senha Incorreta")
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    abas_admin = st.sidebar.tabs(["📝 Venda", "✏️ Editar", "⚙️ Config"])
    
    with abas_admin[0]: # VENDER
        livres = [n for n in range(1, int(dados["config"]["total_numeros"])+1) if str(n) not in dados["vendas"]]
        with st.form("venda_rapida", clear_on_submit=True):
            nums_sel = st.multiselect("Números", livres)
            nome_sel = st.text_input("Nome")
            tel_sel = st.text_input("WhatsApp (Ex: 11999998888)")
            pago_sel = st.checkbox("Marcas como Pago?")
            if st.form_submit_button("Registrar Venda"):
                if nums_sel and nome_sel:
                    sh = conectar(); ws = sh.worksheet("vendas")
                    for n in nums_sel:
                        ws.append_row([str(n), nome_sel, tel_sel, str(pago_sel).upper(), datetime.now().strftime("%d/%m/%Y")])
                    st.rerun()

    with abas_admin[1]: # EDITAR / EXCLUIR
        if dados["vendas"]:
            n_ed = st.selectbox("Escolha o Número:", sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][n_ed]
            new_nome = st.text_input("Nome", value=info['nome'])
            new_tel = st.text_input("Tel", value=info['tel'])
            new_pago = st.checkbox("Pago?", value=info['pago'])
            c1, c2 = st.columns(2)
            if c1.button("✅ Atualizar"):
                atualizar_venda_sheet(n_ed, new_nome, new_tel, new_pago); st.rerun()
            if c2.button("🗑️ Excluir"):
                excluir_venda_sheet(n_ed); st.rerun()

    with abas_admin[2]: # CONFIGS
        t_rifa = st.text_input("Título da Rifa", value=dados["config"]["titulo"])
        t_nums = st.number_input("Total Números", value=int(dados["config"]["total_numeros"]))
        t_prec = st.number_input("Preço R$", value=float(dados["config"]["preco"]))
        t_data = st.text_input("Data Sorteio (AAAA-MM-DD HH:MM:SS)", value=dados["config"]["data_sorteio"])
        p1 = st.text_input("1º Prêmio", value=dados["config"]["premio1"])
        p2 = st.text_input("2º Prêmio", value=dados["config"]["premio2"])
        p3 = st.text_input("3º Prêmio", value=dados["config"]["premio3"])
        if st.button("Salvar Configurações"):
            salvar_config_sheet(t_rifa, t_nums, t_prec, p1, p2, p3, t_data); st.rerun()
        if st.checkbox("Liberar Reset"):
            if st.button("🔴 ZERAR TUDO"):
                sh = conectar(); ws = sh.worksheet("vendas"); ws.clear()
                ws.append_row(["numero", "nome", "tel", "pago", "data"]); st.rerun()

# --- INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🎟️ {dados['config']['titulo']}</h1>", unsafe_allow_html=True)

# Cronômetro
try:
    alvo = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    dif = alvo - datetime.now()
    if dif.total_seconds() > 0:
        st.markdown(f"<div class='countdown-box'>⏳ Faltam {dif.days} dias, {dif.seconds//3600}h e {(dif.seconds//60)%60}m para o sorteio!</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='countdown-box' style='background:red; color:white;'>🏁 VENDAS ENCERRADAS!</div>", unsafe_allow_html=True)
except: pass

# Dashboard
vendas = dados["vendas"]
total_n = int(dados["config"]["total_numeros"])
v_count = len(vendas)
p_count = sum(1 for v in vendas.values() if v["pago"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{v_count} ({(v_count/total_n)*100:.1f}%)")
c2.metric("Disponíveis", total_n - v_count)
c3.metric("Confirmado", f"R$ {p_count * float(dados['config']['preco']):.2f}")
c4.metric("A Receber", f"R$ {(v_count - p_count) * float(dados['config']['preco']):.2f}")

st.divider()

# Abas Principais
t_mapa, t_sorteio, t_share, t_stats = st.tabs(["🗺️ Mapa", "🎲 Sorteador", "📢 Divulgação", "📊 Relatório"])

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
                            st.write(f"👤 **Dono:** {v['nome']}")
                            if st.session_state.autenticado and v['tel']:
                                t_l = re.sub(r'\D', '', v['tel'])
                                msg = urllib.parse.quote(f"Olá {v['nome']}, confirmando seu número {n} na {dados['config']['titulo']}!")
                                st.markdown(f'<a href="https://wa.me/55{t_l}?text={msg}" target="_blank" class="btn-whatsapp"><i class="fab fa-whatsapp"></i> WhatsApp</a>', unsafe_allow_html=True)
                    else:
                        with st.popover(f"{n:02d} 🟡", use_container_width=True):
                            st.write("✨ **Livre!**")

with t_sorteio:
    st.subheader("🎲 Sorteio Oficial")
    if st.button("🗑️ Resetar Ganhadores"): st.session_state.vencedores = {}; st.rerun()
    
    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    col_p1, col_p2, col_p3 = st.columns(3)
    
    def animar(lista):
        ph = st.empty()
        for i in range(3,0,-1): ph.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True); time.sleep(1)
        res = random.choice(lista); st.balloons(); return res

    with col_p3:
        st.write(f"3º: {dados['config'].get('premio3')}")
        if st.button("Sortear 3º"):
            if pagos_l:
                r = animar(pagos_l); st.session_state.vencedores["3"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "3" in st.session_state.vencedores: 
            v = st.session_state.vencedores["3"]; st.success(f"🥉 {v['n']} - {v['nome']}")

    with col_p2:
        st.write(f"2º: {dados['config'].get('premio2')}")
        if st.button("Sortear 2º"):
            lf = [n for n in pagos_l if n != st.session_state.vencedores.get("3",{}).get("n")]
            if lf:
                r = animar(lf); st.session_state.vencedores["2"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "2" in st.session_state.vencedores: 
            v = st.session_state.vencedores["2"]; st.success(f"🥈 {v['n']} - {v['nome']}")

    with col_p1:
        st.write(f"1º: {dados['config'].get('premio1')}")
        if st.button("Sortear 1º"):
            lf = [n for n in pagos_l if n not in [st.session_state.vencedores.get(x,{}).get("n") for x in ["2","3"]]]
            if lf:
                r = animar(lf); st.session_state.vencedores["1"] = {"n": r, "nome": vendas[r]["nome"]}; st.rerun()
        if "1" in st.session_state.vencedores: 
            v = st.session_state.vencedores["1"]; st.success(f"🥇 {v['n']} - {v['nome']}")

with t_share:
    st.subheader("📢 Resumo para Grupo")
    pendentes = [f"❌ Nº {n}: {v['nome']}" for n, v in vendas.items() if not v['pago']]
    prog = "🟢" * int((v_count/total_n)*10) + "⚪" * (10 - int((v_count/total_n)*10))
    
    txt = f"*📊 ATUALIZAÇÃO: {dados['config']['titulo']}*\n\n"
    txt += f"📈 *Progresso:* {prog} ({int((v_count/total_n)*100)}%)\n"
    txt += f"✅ Vendidos: {v_count}/{total_n}\n⏳ Restantes: {total_n - v_count}\n\n"
    if pendentes:
        txt += "*⚠️ AGUARDANDO PAGAMENTO:*\n" + "\n".join(pendentes[:10]) + (f"\n...e mais {len(pendentes)-10}" if len(pendentes)>10 else "") + "\n\n"
    txt += "🔗 *Link do Site:* https://sua-rifa.streamlit.app"
    
    st.text_area("Copie o texto:", value=txt, height=200)
    msg_u = urllib.parse.quote(txt)
    st.markdown(f'<a href="https://wa.me/?text={msg_u}" target="_blank" class="btn-share"><i class="fab fa-whatsapp"></i> Postar no Grupo</a>', unsafe_allow_html=True)

with t_stats:
    st.subheader("📋 Relatório Geral")
    if vendas:
        df = pd.DataFrame.from_dict(vendas, orient='index').reset_index()
        df.columns = ['Nº', 'Nome', 'WhatsApp', 'Pago', 'Data']
        st.dataframe(df.sort_values(by="Nº", key=lambda x: x.astype(int)), use_container_width=True)
