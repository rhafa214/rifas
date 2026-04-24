import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time
import urllib.parse
import re
from PIL import Image, ImageDraw, ImageFont
import io

# --- 1. INICIALIZAÇÃO DE SESSÃO (DEVE VIR ANTES DE TUDO) ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}
if 'mostrar_modal' not in st.session_state: st.session_state.mostrar_modal = False
if 'venc_temp' not in st.session_state: st.session_state.venc_temp = {}

# --- 2. CONFIGURAÇÕES BÁSICAS ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"
st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- 3. ESTILOS E SCRIPTS CONSOLIDADOS ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
        .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
        .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; }
        .btn-whatsapp { display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; margin-top: 10px; transition: 0.3s; }
        .btn-whatsapp:hover { background-color: #128C7E; transform: scale(1.02); }
        .btn-share { display: inline-flex; align-items: center; justify-content: center; background-color: #007bff; color: white !important; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; }
        
        /* Overlay de Ganhador Cinema */
        .overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(12px); z-index: 999999; display: flex; justify-content: center; align-items: center; flex-direction: column; }
        .winner-card-xl { background: linear-gradient(145deg, #1a1a1a, #2d2d2d); padding: 50px; border-radius: 30px; border: 4px solid #FFD700; text-align: center; color: white; box-shadow: 0 0 80px rgba(255, 215, 0, 0.4); animation: pulse 2s infinite; }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }

        /* Popover Amarelo Pendentes */
        div[data-testid="stPopover"] > button { background-color: #FFD700 !important; color: black !important; border: 1px solid #B8860B !important; font-weight: bold !important; width: 100%; }
    </style>

    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
    function dispararConfete() {
        var end = Date.now() + (5 * 1000);
        (function frame() {
            confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0 }, colors: ['#FFD700', '#ffffff'] });
            confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1 }, colors: ['#FFD700', '#ffffff'] });
            if (Date.now() < end) { requestAnimationFrame(frame); }
        }());
    }
    function fecharAutomatico(segundos) {
        setTimeout(function() {
            const botoes = window.parent.document.querySelectorAll('button');
            for (let b of botoes) { if (b.innerText.includes('FECHAR E VOLTAR')) { b.click(); } }
        }, segundos * 1000);
    }
    </script>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES DE DADOS E CONEXÃO ---
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_dict("suas-credenciais.json", scope)
    return gspread.authorize(creds).open(NOME_PLANILHA)

def carregar_dados():
    try:
        sh = conectar()
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
        ws_c = sh.worksheet("config")
        conf_list = ws_c.get_all_records()
        conf = conf_list[0] if conf_list else {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa Master", "data_sorteio": "2024-12-31 20:00:00"}
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro de Conexão: {e}"); return None

def atualizar_venda_sheet(numero, nome, tel, pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, nome); ws.update_cell(cel.row, 3, tel); ws.update_cell(cel.row, 4, str(pago).upper())

def excluir_venda_sheet(numero):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel: ws.delete_rows(cel.row)

def salvar_config_sheet(titulo, total, preco, p1, p2, p3, data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(total)); ws.update_cell(2, 2, float(preco)); ws.update_cell(2, 3, str(titulo))
    ws.update_cell(2, 4, str(p1)); ws.update_cell(2, 5, str(p2)); ws.update_cell(2, 6, str(p3)); ws.update_cell(2, 7, str(data))

# --- 5. FUNÇÕES DE IMAGEM HD ---
def carregar_fonte(tamanho):
    fontes = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf", "arial.ttf"]
    for f in fontes:
        try: return ImageFont.truetype(f, tamanho)
        except: continue
    return ImageFont.load_default()

def gerar_card_ganhador(numero, nome, premio, titulo_rifa, colocacao):
    img = Image.new('RGB', (1000, 1000), color="#1E1E1E")
    draw = ImageDraw.Draw(img)
    f_t = carregar_fonte(45); f_p = carregar_fonte(80); f_n = carregar_fonte(200); f_nom = carregar_fonte(70); f_pre = carregar_fonte(50)
    cor_podio = "#FFD700" if str(colocacao) == "1" else "#C0C0C0" if str(colocacao) == "2" else "#CD7F32"
    draw.text((500, 80), titulo_rifa.upper(), fill="#FFD700", font=f_t, anchor="mm")
    draw.text((500, 200), "PARABÉNS!", fill="#FFFFFF", font=f_p, anchor="mm")
    draw.ellipse([350, 280, 650, 580], outline=cor_podio, width=15)
    draw.text((500, 430), str(numero), fill="#FFFFFF", font=f_n, anchor="mm")
    draw.text((500, 680), nome.upper(), fill=cor_podio, font=f_nom, anchor="mm")
    draw.rectangle([150, 750, 850, 830], fill=cor_podio)
    draw.text((500, 790), f"GANHOU: {premio}", fill="#1E1E1E", font=f_pre, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

def gerar_imagem_rifa(dados_vendas, total_n, titulo):
    largura = 1200; colunas_grid = 10; tamanho_q = 90; espaco = 15; margem = 50
    linhas_grid = (total_n // colunas_grid) + (1 if total_n % colunas_grid != 0 else 0)
    lista_nomes = sorted(dados_vendas.items(), key=lambda x: int(x[0]))
    itens_col = (len(lista_nomes) // 3) + (1 if len(lista_nomes) % 3 != 0 else 0)
    altura_total = 180 + (linhas_grid * (tamanho_q + espaco)) + (max(itens_col, 1) * 45) + 250
    img = Image.new('RGB', (largura, altura_total), color="#FFFFFF"); draw = ImageDraw.Draw(img)
    f_t = carregar_fonte(60); f_n = carregar_fonte(45); f_l = carregar_fonte(24)
    draw.rectangle([0, 0, largura, 180], fill="#1E1E1E")
    draw.text((largura//2, 70), titulo.upper(), fill="#FFC107", font=f_t, anchor="mm")
    x_off = (largura - (colunas_grid * (tamanho_q + espaco) - espaco)) // 2
    for i in range(total_n):
        n_s = str(i+1)
        cor = "#2ECC71" if n_s in dados_vendas and dados_vendas[n_s]['pago'] else "#E74C3C" if n_s in dados_vendas else "#E0E0E0"
        x = x_off + (i % colunas_grid) * (tamanho_q + espaco); y = 230 + (i // colunas_grid) * (tamanho_q + espaco)
        draw.rectangle([x, y, x + tamanho_q, y + tamanho_q], fill=cor)
        draw.text((x + tamanho_q//2, y + tamanho_q//2), f"{i+1:02d}", fill="white" if cor != "#E0E0E0" else "#333", font=f_n, anchor="mm")
    buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); return buf.getvalue()

# --- 6. CARREGAMENTO DE DADOS ---
dados = carregar_dados()
if not dados: st.stop()
vendas = dados["vendas"]; config = dados["config"]; total_n = int(config["total_numeros"])

# --- 7. PAINEL ADMINISTRATIVO ---
st.sidebar.title("🔐 Painel Administrativo")
if not st.session_state.autenticado:
    if st.sidebar.text_input("Senha Admin:", type="password") == SENHA_MESTRE:
        st.session_state.autenticado = True; st.rerun()
else:
    if st.sidebar.button("🚪 Sair"): st.session_state.autenticado = False; st.rerun()
    st.sidebar.divider()
    adm_tabs = st.sidebar.tabs(["📝 Venda", "✏️ Editar", "⚙️ Config"])
    with adm_tabs[0]:
        livres = [n for n in range(1, total_n+1) if str(n) not in vendas]
        with st.form("venda_r"):
            n_sel = st.multiselect("Números", livres); n_nom = st.text_input("Nome"); n_tel = st.text_input("WhatsApp"); n_pg = st.checkbox("Pago?")
            if st.form_submit_button("Registrar"):
                sh = conectar(); ws = sh.worksheet("vendas")
                for n in n_sel: ws.append_row([str(n), n_nom, n_tel, str(n_pg).upper(), datetime.now().strftime("%d/%m/%Y")])
                st.rerun()
    with adm_tabs[1]:
        if vendas:
            n_ed = st.selectbox("Editar Número:", sorted(vendas.keys(), key=int))
            ed_nom = st.text_input("Nome", value=vendas[n_ed]['nome']); ed_tel = st.text_input("Tel", value=vendas[n_ed]['tel']); ed_pg = st.checkbox("Pago?", value=vendas[n_ed]['pago'])
            c1, c2 = st.columns(2)
            if c1.button("✅ Atualizar"): atualizar_venda_sheet(n_ed, ed_nom, ed_tel, ed_pg); st.rerun()
            if c2.button("🗑️ Excluir"): excluir_venda_sheet(n_ed); st.rerun()
    with adm_tabs[2]:
        t_rifa = st.text_input("Título", value=config["titulo"]); t_nums = st.number_input("Total", value=int(config["total_numeros"]))
        t_prec = st.number_input("Preço", value=float(config["preco"])); t_data = st.text_input("Data (AAAA-MM-DD HH:MM:SS)", value=config["data_sorteio"])
        p1 = st.text_input("1º Prêmio", value=config["premio1"]); p2 = st.text_input("2º Prêmio", value=config["premio2"]); p3 = st.text_input("3º Prêmio", value=config["premio3"])
        if st.button("Salvar Configurações"): salvar_config_sheet(t_rifa, t_nums, t_prec, p1, p2, p3, t_data); st.rerun()
        if st.checkbox("Zerar Dados?"):
            if st.button("🔴 RESET TOTAL"):
                sh = conectar(); ws = sh.worksheet("vendas"); ws.clear(); ws.append_row(["numero", "nome", "tel", "pago", "data"]); st.rerun()

# --- 8. INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🏆 {config['titulo']}</h1>", unsafe_allow_html=True)

# Cronômetro
try:
    alvo = datetime.strptime(config["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    dif = alvo - datetime.now()
    if dif.total_seconds() > 0:
        st.markdown(f"<div class='countdown-box'>⏳ Faltam {dif.days} dias, {dif.seconds//3600}h e {(dif.seconds//60)%60}m para o sorteio!</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='countdown-box' style='background:red; color:white;'>🏁 VENDAS ENCERRADAS!</div>", unsafe_allow_html=True)
except: pass

# Dashboard
v_count = len(vendas); p_count = sum(1 for v in vendas.values() if v["pago"])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{v_count} ({(v_count/total_n)*100:.1f}%)")
c2.metric("Disponíveis", total_n - v_count)
c3.metric("Confirmado", f"R$ {p_count * float(config['preco']):.2f}")
c4.metric("A Receber", f"R$ {(v_count - p_count) * float(config['preco']):.2f}")

st.divider()

t_mapa, t_sorteio, t_share, t_pendentes = st.tabs(["🗺️ Mapa", "🎲 Sorteio", "📢 Divulgação", "⚠️ Pendentes"])

with t_mapa:
    busca = st.text_input("🔍 Consultar Meus Números (Nome ou WhatsApp):")
    resultados = {n: v for n, v in vendas.items() if busca.lower() in v['nome'].lower() or busca in v['tel']} if busca else {}
    if resultados:
        st.success(f"✅ Encontramos {len(resultados)} números para '{busca}': {', '.join(resultados.keys())}")
    
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Disponível")
    num_cols = 10
    for i in range(0, total_n, num_cols):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            n = i + j + 1
            if n <= total_n:
                n_s = str(n)
                with cols[j]:
                    if n_s in vendas:
                        v = vendas[n_s]
                        cor = "🟢" if v['pago'] else "🔴"
                        with st.popover(f"{n:02d} {cor}", use_container_width=True):
                            st.write(f"👤 **Dono:** {v['nome']}")
                            if st.session_state.autenticado and v['tel']:
                                t_l = re.sub(r'\D', '', v['tel'])
                                msg = urllib.parse.quote(f"Olá {v['nome']}, confirmando seu número {n} na {config['titulo']}!")
                                st.markdown(f'<a href="https://wa.me/55{t_l}?text={msg}" target="_blank" class="btn-whatsapp"><i class="fab fa-whatsapp"></i> WhatsApp</a>', unsafe_allow_html=True)
                    else: st.button(f"{n:02d} 🟡", key=f"btn_l_{n}", disabled=True, use_container_width=True)

with t_sorteio:
    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    c1, c2, c3 = st.columns(3)
    def iniciar_sorteio(lista, premio_nome, chave):
        ph = st.empty()
        for _ in range(20):
            ph.markdown(f"<h1 style='text-align:center; font-size:100px; color:#FFD700;'>{random.choice(lista)}</h1>", unsafe_allow_html=True); time.sleep(0.1)
        v_n = random.choice(lista); ph.empty()
        st.session_state.venc_temp = {"n": v_n, "nome": vendas[v_n]["nome"], "premio": premio_nome, "chave": chave}
        st.session_state.vencedores[chave] = st.session_state.venc_temp
        st.session_state.mostrar_modal = True; st.rerun()

    if c3.button("Sortear 3º 🥉", use_container_width=True): iniciar_sorteio(pagos_l, config.get('premio3'), "3")
    if c2.button("Sortear 2º 🥈", use_container_width=True): iniciar_sorteio([n for n in pagos_l if n != st.session_state.vencedores.get("3",{}).get("n")], config.get('premio2'), "2")
    if c1.button("Sortear 1º 🥇", use_container_width=True): iniciar_sorteio([n for n in pagos_l if n not in [st.session_state.vencedores.get(x,{}).get("n") for x in ["2","3"]]], config.get('premio1'), "1")

    if st.session_state.get('mostrar_modal'):
        v = st.session_state.venc_temp
        st.markdown(f"""<div class='overlay'><div class='winner-card-xl'><h2 style='color:#FFD700;'>🏆 {v['premio']} 🏆</h2><p style='font-size:150px; font-weight:900;'>{v['n']}</p><p style='font-size:50px;'>{v['nome']}</p><p style='color:#888;'>Fecha em 15s...</p></div></div><script>dispararConfete(); fecharAutomatico(15);</script>""", unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns([1,2,1])
        with col_m2:
            if st.button("❌ FECHAR E VOLTAR", type="primary", use_container_width=True): st.session_state.mostrar_modal = False; st.rerun()
            c_bytes = gerar_card_ganhador(v['n'], v['nome'], v['premio'], config['titulo'], v['chave'])
            st.download_button("📥 BAIXAR CARD GANHADOR", c_bytes, f"ganhador_{v['n']}.png", use_container_width=True)

    if st.session_state.vencedores and not st.session_state.mostrar_modal:
        st.divider(); st.subheader("📜 Resultados Confirmados")
        cols_v = st.columns(3)
        for i, k in enumerate(["1", "2", "3"]):
            if k in st.session_state.vencedores:
                res = st.session_state.vencedores[k]
                with cols_v[i]:
                    st.info(f"**{k}º Lugar:** {res['n']} - {res['nome']}")
                    st.download_button(f"📥 Card {k}º", gerar_card_ganhador(res['n'], res['nome'], res['premio'], config['titulo'], k), f"card_{k}.png", key=f"dl_f_{k}")

with t_share:
    st.subheader("📢 Gerar Divulgação")
    if st.button("🖼️ Gerar Mapa Atualizado HD"):
        with st.spinner("Criando..."):
            img_b = gerar_imagem_rifa(vendas, total_n, config['titulo'])
            st.image(img_b); st.download_button("📥 Baixar Mapa PNG", img_b, "mapa_rifa.png", use_container_width=True)
    
    st.divider()
    prog = "🟢" * (int((v_count/total_n)*10)) + "⚪" * (10 - int((v_count/total_n)*10))
    txt = f"*📊 ATUALIZAÇÃO: {config['titulo']}*\n📈 *Progresso:* {prog} ({int((v_count/total_n)*100)}%)\n✅ Vendidos: {v_count}/{total_n}\n💰 Pagos: {p_count}\n⏳ Pendentes: {v_count-p_count}\n🟡 Livres: {total_n-v_count}\n\n"
    pends_list = [f"• Nº {n}: {v['nome']}" for n, v in vendas.items() if not v['pago']]
    if pends_list: txt += "*⚠️ AGUARDANDO PGTO:*\n" + "\n".join(pends_list[:10]) + "\n\n"
    txt += "🔗 *Reserve aqui:* https://sua-rifa.streamlit.app"
    st.text_area("Legenda:", value=txt, height=200)
    st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(txt)}" target="_blank" class="btn-share"><i class="fab fa-whatsapp"></i> Postar no Grupo</a>', unsafe_allow_html=True)

with t_pendentes:
    st.subheader("🟡 Gestão de Pagamentos")
    pends_dict = {n: v for n, v in vendas.items() if not v['pago']}
    if not pends_dict: st.success("Tudo pago! 🚀")
    else:
        for n_p, v_p in sorted(pends_dict.items(), key=lambda x: int(x[0])):
            c_n, c_nom, c_ac = st.columns([0.8, 2, 1.5])
            c_n.markdown(f"### `{n_p:0>2}`"); c_nom.markdown(f"**{v_p['nome']}**\n\n{v_p['tel']}")
            with c_ac.popover("🟡 PENDENTE", use_container_width=True):
                if st.button("Confirmar ✅", key=f"cp_{n_p}", type="primary"):
                    atualizar_venda_sheet(n_p, v_p['nome'], v_p['tel'], True); st.toast("Pago!"); time.sleep(0.5); st.rerun()
            st.divider()
